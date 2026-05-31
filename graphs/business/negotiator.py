# graphs/business/negotiator.py
import logging
import json
import uuid
from sqlalchemy.orm import Session
from core.dependencies import get_session
from core.ollama_client import generate_text
from core.rag import retrieve_chunks_reranked
from core.db_services import get_product_context
from core.decision_logger import log_decision
from core.utils import parse_llm_json, load_prompt
from graphs.supervisor.state import AgencyState
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger("graphs_negotiator")
logging.basicConfig(level=logging.INFO)

# Prompt is loaded dynamically from prompts/business/negotiator_system.txt

def negotiator_node(state: AgencyState) -> dict:
    """
    Negotiator Agent Node (v3.2).
    Proactively negotiates campaign budget, target CPA and notes with CMO.
    Uses RAG retrieval for past performance metrics and case studies.
    """
    logger.info("Executing Proactive Negotiator Node...")
    with get_session() as db:
    
        workspace_id = state.get("workspace_id")
        product_id = state.get("product_id")
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
            case_studies_str = "(Không có Case Study phù hợp nào được tìm thấy)"
            
        # 3. Retrieve draft history
        draft = state.get("draft_plan") or {}
        current_budget = draft.get("test_budget") or state.get("test_budget") or 2000000.0
        current_cpa = draft.get("target_cpa") or state.get("target_cpa") or 150000.0
        current_notes = draft.get("notes_for_creative") or ""
        
        # 4. Construct history
        messages = state.get("messages", [])
        recent_messages = messages[-6:]
        history_lines = []
        for msg in recent_messages:
            role = "Sếp" if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human" else "Negotiator"
            history_lines.append(f"{role}: {msg.content}")
        history_str = "\n".join(history_lines)
    
        # 5. Build prompt and invoke LLM
        negotiator_template = load_prompt("business", "negotiator_system.txt")
        prompt = negotiator_template.format(
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
            result = parse_llm_json(response_str)
        except Exception as e:
            logger.error(f"Error calling LLM for negotiation: {e}")
            raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e
        
        updated_plan = result.get("updated_draft_plan", {})
    
        # Tool invocation log (SOP discipline)
        log_decision(
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            agent_name="Negotiator Agent",
            action="Negotiate Budget & CPA",
            decision_status="success",
            reason=f"Đàm phán thành công. Ngân sách mới: {updated_plan.get('test_budget')} VNĐ, CPA mới: {updated_plan.get('target_cpa')} VNĐ.",
            metadata=result
        )
        
        # Enforce strict float typing for float operations
        test_budget = float(updated_plan.get("test_budget", current_budget))
        target_cpa = float(updated_plan.get("target_cpa", current_cpa))
        
        ans_msg = result.get("agent_message", "Dạ em đã ghi nhận ý kiến của Sếp. Em gửi lại bản thảo đã tối ưu.")
        
        return {
            "test_budget": test_budget,
            "target_cpa": target_cpa,
            "draft_plan": {
                "test_budget": test_budget,
                "target_cpa": target_cpa,
                "notes_for_creative": updated_plan.get("notes_for_creative", current_notes)
            },
            "messages": [AIMessage(content=ans_msg)],
            "sop_stage": "negotiation"
        }
