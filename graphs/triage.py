# graphs/triage.py
import logging
from db.connection import SessionLocal
from core.models import IntentRoutingKnowledge
from core.ollama_client import get_embedding
from core.decision_logger import log_decision
from graphs.state import AgencyState

logger = logging.getLogger("graphs_triage")
logging.basicConfig(level=logging.INFO)

def triage_node(state: AgencyState) -> dict:
    """
    Triage Node (Supervisor) at the entry gateway.
    Classifies user message intent into 'chat', 'show_metrics', 'create_campaign', or 'research'.
    Uses database-driven vector similarity matching via pgvector cosine distance.
    """
    logger.info("Executing Triage Node (Database-Driven Vector Router)...")
    
    # Retrieve last user message
    messages = state.get("messages", [])
    if not messages:
        return {"sop_stage": "triage", "intent_classification": "research"}
        
    query = messages[-1].content.strip()
    
    intent = "research" # Fallback safe default (RAG QA)
    db = SessionLocal()
    
    try:
        query_vector = get_embedding(query)
        
        # Calculate cosine distance using pgvector operator
        distance_expr = IntentRoutingKnowledge.embedding.cosine_distance(query_vector)
        
        # Fetch closest matching utterance
        closest_match_data = db.query(IntentRoutingKnowledge, distance_expr).filter(
            IntentRoutingKnowledge.is_active == True
        ).order_by(distance_expr).first()
        
        if closest_match_data:
            record, distance = closest_match_data
            logger.info(f"Closest match utterance: '{record.utterance}' with cosine distance: {distance:.4f}")
            
            # Threshold check: distance < 0.30 (equivalent to similarity > 0.70)
            if distance < 0.30:
                intent = record.intent_category
                logger.info(f"Semantic Match Found: '{record.utterance}' -> Intent: {intent}")
            else:
                logger.warning(f"Closest match distance {distance:.4f} exceeds threshold 0.30. Fallback to 'research'.")
        else:
            logger.warning("No dynamic utterances found in intent_routing_knowledge table.")
            
    except Exception as e:
        logger.error(f"Semantic Router DB Error: {e}. Falling back to default 'research'.")
        raise RuntimeError(f"Lỗi hệ thống cửa ngõ: Không thể thực hiện phân tích định tuyến vector CSDL: {e}") from e
    finally:
        db.close()
        
    # Assign active UI channel based on intent
    channel = "#phong-sang-tao" if intent == "research" else "#phong-kinh-doanh"
    
    # Log triage routing decision
    ws_id = state.get("workspace_id") or "00000000-0000-0000-0000-000000000002"
    log_decision(
        workspace_id=ws_id,
        agent_name="Triage Node",
        action="Route Intent",
        decision_status="success",
        reason=f"Phân loại tin nhắn thành intent '{intent}'. Kênh điều hướng: {channel}",
        metadata={"intent": intent, "query": query}
    )
    
    return {
        "sop_stage": "triage",
        "intent_classification": intent,
        "current_channel": channel
    }

def route_after_triage(state: AgencyState) -> str:
    """
    Evaluates the classified intent in state and routes to the correct node.
    """
    intent = state.get("intent_classification", "research")
    logger.info(f"Conditional Router: routing state based on intent '{intent}'")
    if intent == "create_campaign":
        return "analyst"
    elif intent == "show_metrics":
        return "performance"
    elif intent == "research":
        return "researcher_agent"
    return "end"
