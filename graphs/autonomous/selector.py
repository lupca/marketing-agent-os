# graphs/autonomous/selector.py
import logging
import random
from graphs.supervisor.state import AgencyState
from graphs.autonomous.telemetry import instrument_node

logger = logging.getLogger("autonomous_nodes")

@instrument_node("selector")
def action_selector_node(state: AgencyState) -> dict:
    """
    Action Selector Node: Determines the precise creative production mix.
    Applies the 80% Exploit / 20% Explore output mix instruction.
    For a target of 5 variants:
      - 4 Exploit variants (using the top MAB angle)
      - 1 Explore variant (using a random explore angle)
    """
    logger.info("Executing Action Selector Node...")
    actions = state.get("selected_actions") or []
    
    if not actions:
        raise ValueError("No creative angles provided by MAB. Cannot form production mix.")
    
    exploit_angle = actions[0]["angle"]
    explore_angles = [a["angle"] for a in actions[1:]]
    if not explore_angles:
        explore_angles = [exploit_angle]
        
    # 80/20 Creative Diversity mix
    mix = [exploit_angle] * 4 + [random.choice(explore_angles)] * 1
        
    logger.info(f"Creative Production Mix formulated: {mix}")
    return {
        "selected_actions": [{"angle": angle} for angle in mix],
        "sop_stage": "creative_generation"
    }
