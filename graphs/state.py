# graphs/state.py
from typing import TypedDict, List, Annotated, Dict, Any, Optional
from langchain_core.messages import BaseMessage
import operator

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
    current_angle: Dict[str, Any]        # Master Brief Angle from Strategist
    master_content: Dict[str, Any]       # Core message from Copywriter
    variants: List[Dict[str, Any]]       # Generated platform-specific kịch bản
    feedback_log: List[str]              # Logs for Guardian review iteration
    intent_classification: str           # Classified intent: 'chat', 'show_metrics', 'create_campaign', 'research'
    is_follow_up: bool                   # True nếu tin nhắn là tiếp nối chủ đề trước (context-aware routing)
    extracted_entities: Dict[str, Any]   # Entities bóc tách từ Triage (budget, product_name, platform...)
    routing_thought_process: str         # Chain-of-Thought suy luận của Triage Router (Observability)

