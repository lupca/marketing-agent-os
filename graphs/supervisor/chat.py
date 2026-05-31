# graphs/chat.py
"""
Chat Agent Node — Xử lý intent 'chat' (hội thoại thông thường).
Trả lời thân thiện, hướng dẫn user sử dụng hệ thống khi cần.
"""
import logging
import uuid
from langchain_core.messages import AIMessage
from core.db_services import get_brand_context, get_product_context
from core.utils import load_prompt
from core.ollama_client import generate_text
from core.decision_logger import log_decision
from graphs.supervisor.state import AgencyState

logger = logging.getLogger("graphs_chat")
logging.basicConfig(level=logging.INFO)


def chat_node(state: AgencyState) -> dict:
    """
    Chat Agent Node.
    Xử lý hội thoại thông thường — chào hỏi, hỏi về tính năng, câu hỏi tổng quát.
    Intent: 'chat' → router dẫn vào đây.
    """
    logger.info("Executing Chat Agent Node (Unified DB Services)...")

    messages = state.get("messages", [])
    query = messages[-1].content.strip() if messages else "Xin chào!"

    ws_id = state.get("workspace_id")
    prod_id = state.get("product_id")
    
    brand = get_brand_context(uuid.UUID(str(ws_id)))
    product = get_product_context(uuid.UUID(str(prod_id)))
    
    brand_info = f"Tên thương hiệu: {brand.get('brand_name', '')} | Định hướng/Slogan: {brand.get('slogan', '')}"
    product_info = f"Tên sản phẩm: {product.get('name', '')} | Mô tả: {product.get('description', '')} | USP: {product.get('usp', '')}"

    # 2. Load and format the dynamic Chat System Prompt
    chat_system_template = load_prompt("supervisor", "chat_system.txt")
    chat_system_prompt = chat_system_template.format(
        brand_info=brand_info,
        product_info=product_info
    )

    try:
        response = generate_text(
            prompt=query,
            system_prompt=chat_system_prompt,
            workspace_id=ws_id
        )

        log_decision(
            workspace_id=ws_id,
            agent_name="Chat Agent",
            action="Chat Response",
            decision_status="success",
            reason=f"Trả lời hội thoại thông thường: '{query[:80]}...' " if len(query) > 80 else f"Trả lời hội thoại thông thường: '{query}'",
            metadata={"query": query, "brand": brand_info, "product": product_info}
        )

        return {
            "sop_stage": "chat",
            "messages": [AIMessage(content=response)]
        }

    except Exception as e:
        logger.error(f"Chat Agent Error: {e}")
        fallback = "Xin chào! Tôi là Marketing Agent OS. Tôi có thể giúp bạn tạo chiến dịch, xem báo cáo hoặc tra cứu chính sách quảng cáo. Bạn muốn làm gì hôm nay?"
        return {
            "sop_stage": "chat",
            "messages": [AIMessage(content=fallback)]
        }
