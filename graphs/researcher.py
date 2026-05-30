# graphs/researcher.py
"""
LangGraph Node: Researcher Agent (RAG-based Policy Research)

Cập nhật v2: Dùng retrieve_chunks_reranked() từ rag.py mới.
Zero-JOIN query trên bảng rag_chunks với access_tags filter.
"""
import logging
from db.connection import SessionLocal
from core.rag import retrieve_chunks_reranked
from core.ollama_client import generate_text
from graphs.state import AgencyState
from langchain_core.messages import AIMessage

logger = logging.getLogger("graphs_researcher")
logging.basicConfig(level=logging.INFO)

# Tags mặc định cho Researcher Agent
RESEARCHER_ACCESS_TAGS = ["marketing", "economics", "psychology", "policies", "global"]


def run_research(workspace_id: str, query: str, access_tags: list = None) -> str:
    """
    Performs vector retrieval (Zero-JOIN) and synthesizes a professional research report
    using Ollama's Qwen2.5 model.

    Args:
        workspace_id: UUID của workspace (multi-tenant isolation)
        query: Câu hỏi/truy vấn của người dùng
        access_tags: Danh sách tags Agent có quyền truy cập.
                     Mặc định: RESEARCHER_ACCESS_TAGS (marketing + policies + ...)
    """
    db = SessionLocal()
    try:
        tags = access_tags or RESEARCHER_ACCESS_TAGS
        logger.info(f"[run_research] query='{query[:60]}', tags={tags}")

        # Zero-JOIN retrieval từ rag_chunks
        results = retrieve_chunks_reranked(
            db=db,
            workspace_id=workspace_id,
            query=query,
            access_tags=tags,
            limit=3,
        )

        if not results:
            logger.warning(f"[run_research] Không tìm thấy kết quả cho: '{query}'")
            return "Không tìm thấy bất kỳ tài liệu chính sách hoặc tri thức liên quan trong CSDL nội bộ."

        # Xây dựng context blocks từ chunks
        context_blocks = []
        for i, r in enumerate(results):
            tags_str = ", ".join(r.get("access_tags", []))
            score = r.get("similarity_score", 0)
            context_blocks.append(
                f"--- TÀI LIỆU {i+1} (Tags: [{tags_str}] | Điểm: {score:.3f}) ---\n"
                f"{r.get('content')}"
            )
        context_str = "\n\n".join(context_blocks)

        # Prompt synthesis
        prompt = (
            f"Bạn là Trợ lý Nghiên cứu Chính sách & Quảng cáo (Researcher Agent) của CMO.\n"
            f"Dựa trên các tài liệu chính sách và tri thức thực tế được truy xuất dưới đây, "
            f"hãy tổng hợp một câu trả lời chuyên sâu, đầy đủ, có số liệu và danh sách cụ thể "
            f"để giải đáp câu hỏi của người dùng.\n\n"
            f"TÀI LIỆU TRUY XUẤT ĐƯỢC:\n"
            f"{context_str}\n\n"
            f"CÂU HỎI CỦA NGƯỜI DÙNG:\n"
            f"\"{query}\"\n\n"
            f"YÊU CẦU TRẢ LỜI:\n"
            f"1. Trả lời bằng Tiếng Việt chuyên nghiệp, rõ ràng, gãy gọn, có định dạng Markdown đẹp mắt.\n"
            f"2. Nêu bật các từ khóa cấm, cơ chế quét tự động của nền tảng (Facebook/TikTok) và hậu quả đối với tài khoản quảng cáo.\n"
            f"3. Đưa ra lời khuyên thực tế giúp nhà quảng cáo lách hoặc tránh vi phạm một cách an toàn.\n"
            f"4. Không bịa đặt thông tin không có trong tài liệu.\n\n"
            f"BÁO CÁO PHÂN TÍCH CHI TIẾT:"
        )

        logger.info("[run_research] Calling Ollama to synthesize research report...")
        report = generate_text(
            prompt,
            system_prompt="Bạn là Researcher Agent chuyên nghiệp. Hãy viết báo cáo phân tích tri thức chất lượng cao."
        )
        return report.strip()

    except Exception as e:
        logger.error(f"[run_research] FATAL ERROR: {e}", exc_info=True)
        raise RuntimeError(f"Lỗi truy xuất hoặc xử lý tri thức Researcher Agent: {str(e)}") from e
    finally:
        db.close()


def researcher_node(state: AgencyState) -> dict:
    """LangGraph Node cho Researcher Agent."""
    logger.info("Executing Researcher Node (Zero-JOIN RAG Policy Research)...")
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("Lỗi hệ thống: Danh sách tin nhắn rỗng.")

    last_msg = messages[-1].content
    workspace_id = state.get("workspace_id")

    try:
        report = run_research(workspace_id, last_msg)
        return {
            "messages": [AIMessage(content=report)],
            "sop_stage": "triage"
        }
    except Exception as e:
        logger.error(f"Researcher node execution failed: {e}")
        raise
