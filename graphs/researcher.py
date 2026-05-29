# graphs/researcher.py
import logging
from db.connection import SessionLocal
from core.rag import retrieve_knowledge_reranked
from core.ollama_client import generate_text
from graphs.state import AgencyState
from langchain_core.messages import AIMessage

logger = logging.getLogger("graphs_researcher")
logging.basicConfig(level=logging.INFO)

def run_research(workspace_id: str, query: str) -> str:
    """
    Performs vector retrieval and synthesizes a professional, structured research report
    using Ollama's Qwen2.5 model. Strictly handles errors and raises exceptions on failure.
    """
    db = SessionLocal()
    try:
        logger.info(f"Researcher performing search for query: '{query}'...")
        # Search pgvector or SQLite mock
        results = retrieve_knowledge_reranked(db, workspace_id, query, limit=3)
        if not results:
            logger.warning(f"No research findings found for: '{query}'")
            return "Không tìm thấy bất kỳ tài liệu chính sách hoặc tri thức liên quan trong CSDL nội bộ."
        
        # Construct context blocks
        context_blocks = []
        for i, r in enumerate(results):
            context_blocks.append(
                f"--- TÀI LIỆU {i+1}: {r.get('source_name', 'Chưa rõ')} (Thể loại: {r.get('category')}) ---\n"
                f"{r.get('content')}"
            )
        context_str = "\n\n".join(context_blocks)
        
        # Prompt to synthesize
        prompt = (
            f"Bạn là Trợ lý Nghiên cứu Chính sách & Quảng cáo (Researcher Agent) của CMO.\n"
            f"Dựa trên các tài liệu chính sách và tri thức thực tế được truy xuất dưới đây, hãy tổng hợp một câu trả lời chuyên sâu, đầy đủ, có số liệu và danh sách cụ thể để giải đáp câu hỏi của người dùng.\n\n"
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
        
        logger.info("Calling Ollama to synthesize research report...")
        report = generate_text(prompt, system_prompt="Bạn là Researcher Agent chuyên nghiệp. Hãy viết báo cáo phân tích tri thức chất lượng cao.")
        return report.strip()
    except Exception as e:
        logger.error(f"FATAL ERROR in run_research: {e}", exc_info=True)
        # Strictly raise the exception so it propagates and triggers error logging/handling
        raise RuntimeError(f"Lỗi truy xuất hoặc xử lý tri thức Researcher Agent: {str(e)}") from e
    finally:
        db.close()

def researcher_node(state: AgencyState) -> dict:
    """
    LangGraph Node for the Researcher Agent.
    """
    logger.info("Executing Researcher Node (RAG-based Policy Research)...")
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("Lỗi hệ thống: Danh sách tin nhắn rỗng, không có dữ liệu truy vấn.")
        
    last_msg = messages[-1].content
    workspace_id = state.get("workspace_id")
    
    try:
        # Invoke core research synthesis function
        report = run_research(workspace_id, last_msg)
        
        # Return updated messages and state stage
        return {
            "messages": [AIMessage(content=report)],
            "sop_stage": "research"
        }
    except Exception as e:
        logger.error(f"Researcher node execution failed: {e}")
        # Raise the exception so LangGraph / App knows the node crashed
        raise
