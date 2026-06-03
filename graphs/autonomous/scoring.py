# graphs/autonomous/scoring.py
import logging
from graphs.supervisor.state import AgencyState
from graphs.autonomous.telemetry import instrument_node

logger = logging.getLogger("autonomous_nodes")

@instrument_node("scoring")
def scoring_node(state: AgencyState) -> dict:
    """
    Scoring Node: Evaluates each creative angle based on MAB calculated beliefs/priors.
    """
    logger.info("Executing Scoring Node...")
    priors = state.get("current_beliefs") or {}
    
    # Sort and rank psychological angles by priority weight
    ranked_angles = sorted(priors.items(), key=lambda x: x[1], reverse=True)
    selected = [{"angle": angle, "belief": weight} for angle, weight in ranked_angles]
    
    logger.info(f"Angles ranked and scored: {selected}")
    return {
        "selected_actions": selected,
        "sop_stage": "selector"
    }
