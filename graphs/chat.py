# graphs/chat.py
"""
Chat Agent Node — Xử lý intent 'chat' (hội thoại thông thường).
Trả lời thân thiện, hướng dẫn user sử dụng hệ thống khi cần.
"""
import logging
import uuid
from langchain_core.messages import AIMessage
from core.db_services import get_brand_context, get_product_context
from core.ollama_client import generate_text
from core.decision_logger import log_decision
from graphs.state import AgencyState

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

    # 1. Fetch brand and product context from dynamic DB services layer
    ws_id = state.get("workspace_id") or "00000000-0000-0000-0000-000000000002"
    prod_id = state.get("product_id") or "00000000-0000-0000-0000-000000000005"
    
    brand = get_brand_context(uuid.UUID(str(ws_id)))
    product = get_product_context(uuid.UUID(str(prod_id)))
    
    brand_info = f"Tên thương hiệu: {brand['brand_name']} | Định hướng/Slogan: {brand['slogan']}"
    product_info = f"Tên sản phẩm: {product['name']} | Mô tả: {product['description']} | USP: {product['usp']}"

    # 2. Design the dynamic Chat System Prompt
    chat_system_prompt = (
        f"Bạn là trợ lý AI của Marketing Agent OS — một hệ thống quản lý marketing thông minh.\n\n"
        f"## Ngữ cảnh Doanh nghiệp hiện tại:\n"
        f"- **Thương hiệu hiện tại:** {brand_info}\n"
        f"- **Sản phẩm hiện tại:** {product_info}\n\n"
        f"## Tính cách:\n"
        f"- Thân thiện, chuyên nghiệp, ngắn gọn.\n"
        f"- Luôn sẵn sàng giúp đỡ và hướng dẫn người dùng.\n\n"
        f"## Khi người dùng hỏi về Thương hiệu hiện tại hoặc Sản phẩm hiện tại:\n"
        f"- Hãy trả lời chính xác dựa trên thông tin Ngữ cảnh Doanh nghiệp được cung cấp ở trên (ví dụ: thương hiệu hiện tại là 'G-Agent Tech', sản phẩm là 'Marketing Agent OS Software'). Tuyệt đối không bịa đặt hoặc trả lời mơ hồ, không dùng các placeholder như [tên thương hiệu].\n\n"
        f"## Khi người dùng chào hỏi hoặc hỏi tổng quát:\n"
        f"- Chào lại và giới thiệu ngắn gọn bạn có thể làm gì.\n\n"
        f"## Các tính năng bạn có thể hướng dẫn:\n"
        f"1. **Tạo chiến dịch marketing** — 'Lên chiến dịch quảng cáo mới cho [sản phẩm]'\n"
        f"2. **Xem báo cáo hiệu suất** — 'Báo cáo CPA tuần này', 'Kịch bản nào đang đốt tiền?'\n"
        f"3. **Tra cứu chính sách & tài liệu** — 'Facebook cấm từ khóa gì?', 'Chính sách TikTok ngành dược'\n\n"
        f"Hãy trả lời câu hỏi của người dùng bằng Tiếng Việt một cách tự nhiên và hữu ích."
    )

    try:
        response = generate_text(
            prompt=query,
            system_prompt=chat_system_prompt
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
