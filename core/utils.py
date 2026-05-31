# core/utils.py
import json_repair
import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage
from core.decision_logger import log_decision
from core.ollama_client import get_trimmed_context

logger = logging.getLogger("core_utils")

def parse_llm_json(response_str: str, fallback_data: dict) -> dict:
    """
    Cleans and parses the LLM JSON response. 
    If parsing fails, returns fallback_data.
    """
    if not response_str:
        return fallback_data
        
    try:
        # Clean potential markdown block wraps
        cleaned_str = response_str.strip()
        if cleaned_str.startswith("```json"):
            cleaned_str = cleaned_str[7:]
        elif cleaned_str.startswith("```"):
            cleaned_str = cleaned_str[3:]
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3]
        cleaned_str = cleaned_str.strip()
        
        # Repair and load
        data = json_repair.loads(cleaned_str)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
            
        if not isinstance(data, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
            
        return data
    except Exception as e:
        logger.error(f"Error parsing LLM JSON: {e}. Raw response: {response_str[:200]}")
        return fallback_data

def trim_and_log(
    state: Dict[str, Any],
    new_state_data: Dict[str, Any],
    message: str,
    log_action: str,
    agent_name: str = None,
    decision_status: str = "success",
    reason: str = None,
    log_metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Helper to trim context, log decisions to db, and prepare the returned state update.
    """
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    
    # 1. Standard Short-Term Message Trimming logic
    raw_messages = state.get("messages", [])
    get_trimmed_context(raw_messages, max_tokens=14000, workspace_id=str(workspace_id) if workspace_id else None)
    
    # 2. Automatically deduce agent name if not provided
    if not agent_name:
        if "Strategist" in message or "🧠" in message:
            agent_name = "Strategist Agent"
        elif "Copywriter" in message or "✍️" in message:
            agent_name = "Copywriter Agent"
        elif "Guardian" in message or "🛡️" in message:
            agent_name = "Brand Guardian Agent"
        else:
            agent_name = "Agency Agent"
            
    # 3. Log decision
    log_decision(
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        agent_name=agent_name,
        action=log_action,
        decision_status=decision_status,
        reason=reason or message.replace("`", "").replace("*", ""),
        metadata=log_metadata if log_metadata is not None else new_state_data
    )
    
    # 4. Construct response dictionary for LangGraph
    state_update = {**new_state_data}
    state_update["messages"] = [AIMessage(content=message)]
    
    return state_update

def get_integration_config(workspace_id: str, platform_name: str) -> dict:
    """
    Dynamically fetches active integration configurations for a platform in a workspace.
    Returns a key-value dictionary, e.g. {"api_key": "...", "user": "..."}
    """
    from db.connection import SessionLocal
    from core.models import WorkspaceIntegration
    import uuid
    
    db = SessionLocal()
    try:
        ws_uuid = uuid.UUID(str(workspace_id))
        records = db.query(WorkspaceIntegration).filter_by(
            workspace_id=ws_uuid,
            platform_name=platform_name,
            is_active=True
        ).all()
        return {r.config_key: r.config_value for r in records}
    except Exception as e:
        logger.error(f"Error fetching integration config for platform {platform_name}: {e}")
        return {}
    finally:
        db.close()
