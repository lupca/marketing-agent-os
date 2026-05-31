# graphs/creative_reporter.py
"""
Creative Reporter Agent Node — Tổng hợp báo cáo hoạt động sáng tạo.
Truy vấn database thông qua lớp dịch vụ tập trung (core.db_services),
tổng hợp các góc tiếp cận (Angles) và điểm tuân thủ của ban Sáng Tạo.
Gọi Ollama Qwen2.5 để tổng hợp báo cáo phân tích chuyên sâu cho CMO.
"""
import logging
import uuid
from core.db_services import get_creative_report_data
from core.ollama_client import generate_text
from core.decision_logger import log_decision
from graphs.supervisor.state import AgencyState
from langchain_core.messages import AIMessage

logger = logging.getLogger("graphs_creative_reporter")
logging.basicConfig(level=logging.INFO)

def creative_report_node(state: AgencyState) -> dict:
    """
    Creative Reporter Agent Node.
    Truy vấn số liệu từ DB service layer và gọi LLM Qwen2.5 tổng hợp báo cáo sáng tạo.
    """
    logger.info("Executing Creative Reporter Node (DB Services Creative Analysis)...")
    
    workspace_id = state.get("workspace_id")
    ws_uuid = uuid.UUID(str(workspace_id))
    
    try:
        # 1. Truy vấn các thông tin sáng tạo qua DB Service Layer
        data = get_creative_report_data(ws_uuid)
        
        total_angles = data["total_angles"]
        scheduled_copies = data["scheduled_copies"]
        published_copies = data["published_copies"]
        killed_copies = data["killed_copies"]
        scaled_copies = data["scaled_copies"]
        creative_details_str = data["creative_details_str"]
        
        # 2. Load and format the dynamic Creative Reporter Prompt
        from core.utils import load_prompt
        creative_reporter_template = load_prompt("creative", "creative_reporter_system.txt")
        prompt = creative_reporter_template.format(
            total_angles=total_angles,
            scheduled_copies=scheduled_copies,
            published_copies=published_copies,
            killed_copies=killed_copies,
            scaled_copies=scaled_copies,
            creative_details_str=creative_details_str
        )
        
        logger.info("Calling Ollama to synthesize creative activity report...")
        try:
            report = generate_text(
                prompt=prompt,
                system_prompt="Bạn là Creative Reporter Agent chuyên nghiệp. Hãy viết báo cáo đánh giá sáng tạo chất lượng cao.",
                workspace_id=workspace_id
            )
        except Exception as e:
            logger.error(f"Error calling LLM for creative report: {e}")
            raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e
        
        # Log quyết định vào CSDL
        log_decision(
            workspace_id=workspace_id,
            campaign_id=state.get("campaign_id"),
            agent_name="Creative Reporter",
            action="Synthesize Creative Report",
            decision_status="success",
            reason=f"Tổng hợp thành công báo cáo hoạt động sáng tạo dựa trên {total_angles} MasterContent và {scheduled_copies + published_copies + killed_copies + scaled_copies} PlatformVariants.",
            metadata={"total_angles": total_angles, "variants_count": scheduled_copies + published_copies + killed_copies + scaled_copies}
        )
        
        # 3. Trả về và reset sop_stage về triage để tránh kẹt trạng thái hội thoại
        report_msg = (
            f"🎨 **[Ban Sáng Tạo - Creative Reporter]**\n\n"
            f"{report.strip()}"
        )
        return {
            "messages": [AIMessage(content=report_msg)],
            "sop_stage": "triage"
        }
        
    except Exception as e:
        logger.error(f"Error executing creative_report_node: {e}", exc_info=True)
        fallback = "Dạ chào Sếp, em đã cố gắng kết nối CSDL để truy xuất báo cáo của phòng Sáng Tạo nhưng gặp sự cố kết nối. Sếp vui lòng thử lại sau giây lát ạ!"
        return {
            "messages": [AIMessage(content=fallback)],
            "sop_stage": "triage"
        }
