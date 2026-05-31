# graphs/routing_models.py
"""
Pydantic schema cho Intelligent Supervisor Hub (Triage Router).
Bắt buộc LLM phải xuất ra cấu trúc JSON chuẩn — tránh hallucination.
"""
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any


class RoutingDecision(BaseModel):
    """
    Structured output schema cho LLM Triage Router.
    LLM phải điền đầy đủ 4 trường này trước khi hệ thống chấp nhận quyết định định tuyến.
    """

    thought_process: str = Field(
        description=(
            "Suy luận từng bước (Chain-of-Thought): Phân tích lịch sử hội thoại, "
            "trạng thái SOP hiện tại, và ý định thực sự của người dùng. "
            "Bắt buộc điền — không được bỏ trống để tránh ảo giác (hallucination)."
        )
    )

    is_follow_up: bool = Field(
        description=(
            "True nếu tin nhắn này là tiếp nối của chủ đề ngay trước đó "
            "(ví dụ: user đang tạo chiến dịch dở rồi bổ sung thông tin). "
            "False nếu đây là yêu cầu mới hoàn toàn."
        )
    )

    intent: Literal["chat", "show_metrics", "create_campaign", "research", "creative_report"] = Field(
        description=(
            "Intent phân loại cuối cùng. Chỉ chọn một trong 5 giá trị hợp lệ:\n"
            "- 'create_campaign': Tạo chiến dịch, viết kịch bản, brief sáng tạo.\n"
            "- 'show_metrics': Xem báo cáo, số liệu, thống kê hiệu suất ban kinh doanh.\n"
            "- 'creative_report': Xem báo cáo hoạt động, kịch bản, tuân thủ ban sáng tạo.\n"
            "- 'research': Hỏi về chính sách, quy định, từ khóa cấm, tài liệu.\n"
            "- 'chat': Hội thoại thông thường, chào hỏi, câu hỏi tổng quát."
        )
    )

    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Các thông số trích xuất được từ câu lệnh của người dùng. "
            "Ví dụ: {'budget': 5000000, 'product_name': 'G-Agent Tech', "
            "'target_audience': 'SME owners', 'platform': 'TikTok'}. "
            "Để trống {} nếu không trích xuất được thông tin gì."
        )
    )
