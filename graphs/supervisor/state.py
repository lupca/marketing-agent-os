# graphs/supervisor/state.py
from typing import TypedDict, List, Dict, Any, Optional

class AgencyState(TypedDict):
    """
    Stateless AgencyState for the Autonomous Creative Intelligence Engine.
    Holds state for a single execution run, allowing LangGraph to act as an on-demand,
    stateless execution layer.
    """
    # Context injected by Python Backend Orchestrator
    workspace_id: str
    campaign_id: str
    product_id: str
    campaign_objective: str       # 'BRAND_AWARENESS' or 'LEAD_GEN'
    current_metrics: Dict[str, Any]   # Historical performance metrics of latest batch
    current_beliefs: Dict[str, Any]   # MAB calculated beliefs/priors per creative angle
    
    # Internal generation state variables
    sop_stage: str                # Current stage in the automated SOP
    selected_actions: List[Dict[str, Any]]    # Mix of Exploit / Explore creative directions
    generated_variants: List[Dict[str, Any]]  # Generated copies packaged for downstream
    sandbox_feedbacks: List[Dict[str, Any]]   # Brand safety failures and feedback
