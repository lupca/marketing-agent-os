# graphs/negotiator.py
import logging
import json
import uuid
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.ollama_client import generate_text
from core.rag import retrieve_chunks_reranked
from core.db_services import get_product_context
from core.decision_logger import log_decision
from core.utils import parse_llm_json
from graphs.state import AgencyState
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger("graphs_negotiator")
logging.basicConfig(level=logging.INFO)

NEGOTIATOR_SYSTEM_PROMPT = """Bạn là Negotiator Agent đại diện cho ban Kinh Doanh của hệ điều hành Marketing Agent OS.
Nhiệm vụ của bạn là đàm phán trực tiếp với Sếp (CMO) để chốt được Bản thảo (DraftPlan) chất lượng cao nhất cho chiến dịch marketing.

Bản thảo gồm 3 thông số:
1. test_budget (Ngân sách chạy thử - VNĐ)
2. target_cpa (Chi phí chuyển đổi tối đa cho phép - VNĐ)
3. notes_for_creative (Ghi chú định hướng sáng tạo, các ý chỉ chiến thuật của Sếp)

Thông tin kinh tế sản phẩm (Dữ liệu gốc từ CSDL, TUYỆT ĐỐI KHÔNG ĐƯỢC BỊA số liệu):
- Tên sản phẩm: {product_name}
- Giá bán lẻ (Retail Price): {product_price:,.0f} VNĐ
- Chi phí gốc (Cost): {product_cost:,.0f} VNĐ
- Biên lợi nhuận (Margin = Retail Price - Cost): {product_margin:,.0f} VNĐ
- CPA điểm neo tối đa (Calculated Anchor CPA = Margin * 30%): {calculated_anchor_cpa:,.0f} VNĐ

QUY TẮC ĐÀM PHÁN CHỦ ĐỘNG & BẢO TOÀN Ý CHỈ:
1. TRẢ LỜI CHI TIẾT VÀ DẪN CHỨNG SỐ LIỆU CỤ THỂ (RAG):
- Khi giải thích hoặc đề xuất, bạn PHẢI sử dụng dữ liệu RAG được cung cấp bên dưới để làm dẫn chứng số liệu thực tế cụ thể.
- KHÔNG ĐƯỢC trả lời mơ hồ/chung chung kiểu "dựa trên hiệu suất của các chiến dịch trước" hay "các Case Study trước". Bạn PHẢI trích dẫn rõ tên chiến dịch cũ nào (ví dụ: Chiến dịch 'Tối ưu CPA Doanh Nghiệp SMEs' tháng 02/2026), ngân sách chạy thử bao nhiêu, CPA thực tế bao nhiêu để làm thuyết phục Sếp.
- Nếu giải thích lý do tính toán của CPA target ban đầu (ví dụ: 1,050,000đ hay 850,000đ), bạn hãy chỉ rõ công thức kinh tế: Biên lợi nhuận sản phẩm là bao nhiêu, và ban Kinh doanh tính CPA mục tiêu tối đa bằng 30% Biên lợi nhuận để bảo đảm hiệu quả kinh tế.

2. PHÂN BIỆT RÕ HỎI ĐÁP (Q&A) VỚI YÊU CẦU SỬA ĐỔI:
- BẢO TOÀN THÔNG SỐ KHI HỎI ĐÁP: Nếu Sếp đặt câu hỏi ngoài luồng, hỏi lý do, thắc mắc tại sao (ví dụ: "tại sao CPA target là X?", "lý do gì có con số này?"), bạn chỉ tập trung giải thích lý do con số đó trong `agent_message`. Lúc này, bạn BẮT BUỘC phải giữ nguyên giá trị `test_budget` và `target_cpa` hiện tại trong `updated_draft_plan` (KHÔNG tự ý sửa đổi tăng/giảm hay đề xuất thay đổi sang con số khác trừ khi Sếp ra lệnh chỉnh sửa rõ ràng như "sửa thành X", "thay đổi thành Y", "tăng lên X", "giảm xuống Y").
- CHỈ CẬP NHẬT KHI ĐƯỢC YÊU CẦU: Chỉ cập nhật các giá trị của Bản thảo trong `updated_draft_plan` khi Sếp phản hồi đồng ý hoặc yêu cầu sửa đổi các thông số đó rõ ràng.
- GHI NHẬN Ý CHỈ CHIẾN THUẬT: Khi Sếp đưa ra chỉ đạo hoặc định hướng định tính (ví dụ: "tập trung vào tính năng X", "đánh vào nỗi đau Y"), hãy giữ nguyên ngân sách và CPA, đồng thời cập nhật toàn bộ các chỉ đạo này vào `notes_for_creative`.

Dữ liệu lịch sử chiến dịch liên quan (RAG):
{case_studies}

Lịch sử đàm phán gần đây:
{conversation_history}

Bản thảo hiện tại:
- Ngân sách: {current_budget:,.0f} VNĐ
- CPA Target: {current_cpa:,.0f} VNĐ
- Notes cho sáng tạo: "{current_notes}"

Bạn PHẢI trả về phản hồi dưới dạng JSON có cấu trúc chính xác như sau (không kèm markdown, không thêm trường khác):
{{
  "thought_process": "<suy luận từng bước của bạn, phân tích xem Sếp đang hỏi giải thích hay yêu cầu chỉnh sửa thông số để quyết định giữ nguyên hay cập nhật>",
  "updated_draft_plan": {{
    "test_budget": <float - ngân sách hiện tại hoặc ngân sách mới nếu Sếp yêu cầu thay đổi rõ ràng>,
    "target_cpa": <float - CPA hiện tại hoặc CPA mới nếu Sếp yêu cầu thay đổi rõ ràng>,
    "notes_for_creative": "<string - ghi chú chiến thuật hiện tại kết hợp chỉ đạo mới nếu có>"
  }},
  "agent_message": "<phản hồi bằng Tiếng Việt thân thiện, lịch sự và thuyết phục gửi tới Sếp, nêu rõ dẫn chứng số liệu cụ thể hoặc giải thích thắc mắc của Sếp>"
}}"""

def negotiator_node(state: AgencyState) -> dict:
    """
    Negotiator Agent Node (v3.2).
    Proactively negotiates campaign budget, target CPA and notes with CMO.
    Uses RAG retrieval for past performance metrics and case studies.
    """
    logger.info("Executing Proactive Negotiator Node...")
    db: Session = SessionLocal()
    
    workspace_id = state.get("workspace_id") or "00000000-0000-0000-0000-000000000002"
    product_id = state.get("product_id") or "00000000-0000-0000-0000-000000000005"
    campaign_id = state.get("campaign_id")
    
    # 1. Fetch Product details
    product_name = "Sản phẩm AI"
    product_price = 0.0
    product_cost = 0.0
    product_margin = 0.0
    try:
        product = get_product_context(uuid.UUID(str(product_id)))
        product_name = product.get("name", "Sản phẩm AI")
        product_price = product.get("price", 0.0)
        product_cost = product.get("cost", 0.0)
        product_margin = product.get("margin", 0.0)
    except Exception as e:
        logger.error(f"Error fetching product name: {e}")
        
    calculated_anchor_cpa = product_margin * 0.3
        
    # 2. Retrieve relevant Case Studies (RAG)
    query = f"chỉ số hiệu suất CPA ngân sách và kết quả chiến dịch cũ của {product_name}"
    logger.info(f"Negotiator retrieving RAG context for: {query}")
    rag_results = retrieve_chunks_reranked(
        db, 
        uuid.UUID(str(workspace_id)), 
        query, 
        access_tags=["economics", "anti_patterns", "user_upload"], 
        limit=3
    )
    
    case_studies_str = ""
    if rag_results:
        for idx, item in enumerate(rag_results):
            case_studies_str += f"Case Study {idx+1}: {item.get('content')}\n"
    else:
        case_studies_str = "(Không tìm thấy case study cũ trong cơ sở dữ liệu. Vui lòng tự đề xuất chỉ số hợp lý)"
        
    # 3. Read current DraftPlan
    draft = state.get("draft_plan") or {}
    current_budget = draft.get("test_budget") or state.get("test_budget") or 2000000.0
    current_cpa = draft.get("target_cpa") or state.get("target_cpa") or 150000.0
    current_notes = draft.get("notes_for_creative") or ""
    
    # 4. Form conversation history
    messages = state.get("messages", [])
    recent_messages = messages[-6:]
    history_lines = []
    for msg in recent_messages:
        role = "Sếp" if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human" else "Negotiator"
        history_lines.append(f"{role}: {msg.content}")
    history_str = "\n".join(history_lines)
    
    # 5. Build prompt and invoke LLM
    prompt = NEGOTIATOR_SYSTEM_PROMPT.format(
        product_name=product_name,
        product_price=product_price,
        product_cost=product_cost,
        product_margin=product_margin,
        calculated_anchor_cpa=calculated_anchor_cpa,
        case_studies=case_studies_str,
        current_budget=current_budget,
        current_cpa=current_cpa,
        current_notes=current_notes,
        conversation_history=history_str
    )
    
    query_text = messages[-1].content if messages else "Đàm phán bản thảo"
    system_prompt = "You are a master business negotiator. Output JSON only."
    
    try:
        response_str = generate_text(query_text, system_prompt=prompt, json_format=True, workspace_id=workspace_id)
        result = parse_llm_json(response_str, fallback_data={
            "thought_process": "Lỗi phân tích JSON từ LLM. Giữ nguyên chỉ số.",
            "updated_draft_plan": {
                "test_budget": current_budget,
                "target_cpa": current_cpa,
                "notes_for_creative": current_notes
            },
            "agent_message": "Dạ em đã ghi nhận ý kiến của Sếp. Em xin gửi lại bản phác thảo ngân sách và CPA để Sếp duyệt."
        })
    except Exception as e:
        logger.error(f"Error calling LLM for negotiation: {e}")
        result = {
            "thought_process": f"Lỗi gọi LLM: {str(e)}",
            "updated_draft_plan": {
                "test_budget": current_budget,
                "target_cpa": current_cpa,
                "notes_for_creative": current_notes
            },
            "agent_message": "Dạ, hệ thống đang gặp gián đoạn kết nối. Em xin giữ nguyên đề xuất ngân sách chạy thử là 2,000,000đ và CPA mục tiêu là 150,000đ."
        }
        
    updated_plan = result.get("updated_draft_plan", {})
    
    # Tool invocation log (SOP discipline)
    budget_changed = abs(updated_plan.get("test_budget", 0) - current_budget) > 0.01
    cpa_changed = abs(updated_plan.get("target_cpa", 0) - current_cpa) > 0.01
    notes_changed = updated_plan.get("notes_for_creative", "") != current_notes
    
    if budget_changed or cpa_changed or notes_changed:
        logger.info("Draft plan modified! Invoking UpdateDraftPlanTool logger.")
        log_decision(
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            agent_name="Negotiator Agent",
            action="UpdateDraftPlanTool",
            decision_status="success",
            reason=f"Cập nhật Bản thảo đàm phán: Ngân sách={updated_plan.get('test_budget'):,.0f}đ (trước: {current_budget:,.0f}đ), CPA Target={updated_plan.get('target_cpa'):,.0f}đ (trước: {current_cpa:,.0f}đ), Notes: '{updated_plan.get('notes_for_creative')}'",
            metadata={
                "old_budget": current_budget,
                "new_budget": updated_plan.get("test_budget"),
                "old_cpa": current_cpa,
                "new_cpa": updated_plan.get("target_cpa"),
                "notes": updated_plan.get("notes_for_creative")
            }
        )
        
    db.close()
    
    # Return updated state
    return {
        "draft_plan": updated_plan,
        "sop_stage": "waiting_draft_approval",
        "messages": [AIMessage(content=result.get("agent_message", ""))]
    }
