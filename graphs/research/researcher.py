# graphs/researcher.py
"""
LangGraph Node: Researcher Agent (RAG-based Policy Research)

Cập nhật v2: Dùng retrieve_chunks_reranked() từ rag.py mới.
Zero-JOIN query trên bảng rag_chunks với access_tags filter.
"""
import logging
from core.dependencies import get_session
from core.rag import retrieve_chunks_reranked
from core.ollama_client import generate_text
from graphs.supervisor.state import AgencyState
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
    with get_session() as db:
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
            from core.utils import load_prompt
            researcher_template = load_prompt("research", "researcher_system.txt")
            prompt = researcher_template.format(
                context_str=context_str,
                query=query
            )

            logger.info("[run_research] Calling Ollama to synthesize research report...")
            try:
                report = generate_text(
                    prompt,
                    system_prompt="Bạn là Researcher Agent chuyên nghiệp. Hãy viết báo cáo phân tích tri thức chất lượng cao.",
                    workspace_id=workspace_id
                )
            except Exception as e:
                raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e
            return report.strip()

        except Exception as e:
            logger.error(f"[run_research] FATAL ERROR: {e}", exc_info=True)
            raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e
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
