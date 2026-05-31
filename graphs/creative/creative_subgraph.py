# graphs/creative_subgraph.py
import logging
from langgraph.graph import StateGraph, START, END
from graphs.supervisor.state import CreativeState
from graphs.creative.creative import strategist_node, copywriter_node, brand_guardian_node

logger = logging.getLogger("graphs_creative_subgraph")
logging.basicConfig(level=logging.INFO)

def route_after_guardian_in_subgraph(state: CreativeState) -> str:
    """
    Conditional routing inside the Creative Sub-Graph.
    Routes back to copywriter for revisions, or END to return control to the main graph.
    """
    stage = state.get("sop_stage")
    logs = state.get("feedback_log", [])
    
    # Check if maximum review loops exceeded (Max 3 loops to avoid infinite cycle)
    if len(logs) >= 3:
        logger.warning("Max rewrite iterations (3) reached! Automatically passing to CEO review with warning.")
        return "end"
        
    if stage == "waiting_approval":
        return "end"
        
    # Return to Copywriter for revisions
    logger.warning("Feedback rewrite triggered! Routing back to Copywriter Node.")
    return "copywriter"

# Define the Creative Sub-Graph using CreativeState
creative_builder = StateGraph(CreativeState)

# Add Nodes
creative_builder.add_node("strategist", strategist_node)
creative_builder.add_node("copywriter", copywriter_node)
creative_builder.add_node("guardian", brand_guardian_node)

# Add Edges
creative_builder.add_edge(START, "strategist")
creative_builder.add_edge("strategist", "copywriter")
creative_builder.add_edge("copywriter", "guardian")

# Add compliance check conditional router
creative_builder.add_conditional_edges(
    "guardian",
    route_after_guardian_in_subgraph,
    {
        "copywriter": "copywriter",
        "end": END
    }
)

# Compile Creative Sub-Graph
creative_graph = creative_builder.compile()
