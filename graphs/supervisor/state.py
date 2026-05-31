# graphs/state.py
from typing import TypedDict, List, Annotated, Dict, Any, Optional
from langchain_core.messages import BaseMessage
import operator

class DraftPlan(TypedDict):
    test_budget: float
    target_cpa: float
    notes_for_creative: str

class NegotiationState(TypedDict):
    """State này chứa mảng messages đàm phán cồng kềnh"""
    messages: List[BaseMessage]
    draft_plan: DraftPlan
    campaign_id: str
    product_id: str

class BusinessBrief(TypedDict):
    """Cấu trúc dữ liệu sạch, ĐÃ LỌC BỎ RÁC TIN NHẮN"""
    campaign_id: str
    product_id: str
    final_budget: float
    final_cpa: float
    strategic_notes: str

class CreativeState(TypedDict):
    """
    State của phòng Sáng Tạo - Siêu nhẹ, tự quản lý các bản nháp và brainstorm nội bộ.
    """
    messages: List[BaseMessage] # Bắt đầu với mảng rỗng hoặc kế thừa
    workspace_id: str
    campaign_id: str
    product_id: str
    business_context: Dict[str, Any]
    business_brief: BusinessBrief
    sop_stage: str
    killed_variants_feedback: List[Dict[str, Any]]
    
    # 🔒 THE LOCAL STATE: Quá trình "xào nấu" nháp
    current_angle: Dict[str, Any]        # Master Brief Angle từ Strategist
    master_content: Dict[str, Any]       # Core message từ Copywriter
    variants: List[Dict[str, Any]]       # Kịch bản các kênh sau khi viết nháp
    feedback_log: List[str]              # Lịch sử Brand Guardian nhận xét/đánh giá


class AgencyState(TypedDict):
    """
    Global State for the Multi-Agent Marketing Agent OS.
    Ensures SOP tracking, target CPA anchors, and inter-department feedback loop.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    current_channel: str                 # '#phong-kinh-doanh' hoặc '#phong-sang-tao'
    workspace_id: str
    campaign_id: str
    product_id: str
    target_cpa: float                    # Điểm neo sống còn (CPA Target)
    test_budget: float                   # Điểm neo sống còn (Ngân sách test)
    killed_variants_feedback: List[Dict[str, Any]] # Giao thức cãi nhau (Inter-department feedback)
    sop_stage: str                       # 'triage', 'cpa_calculation', 'creative_generation', 'waiting_approval'
    intent_classification: str           # Classified intent: 'chat', 'show_metrics', 'create_campaign', 'research'
    is_follow_up: bool                   # True nếu tin nhắn là tiếp nối chủ đề trước (context-aware routing)
    extracted_entities: Dict[str, Any]   # Entities bóc tách từ Triage (budget, product_name, platform...)
    routing_thought_process: str         # Chain-of-Thought suy luận của Triage Router (Observability)
    
    # 🌟 THE GLOBAL DNA: Kéo 1 lần từ DB, mọi Sub-graph đều được đọc
    business_context: Dict[str, Any]
    
    # State transformation schemas (v3.2)
    draft_plan: DraftPlan
    business_brief: BusinessBrief
    draft_approved: bool                 # True nếu CMO đã bấm duyệt draft plan
    
    # Final output variables to route to downstream approval/publishing
    master_content: Dict[str, Any]
    variants: List[Dict[str, Any]]


