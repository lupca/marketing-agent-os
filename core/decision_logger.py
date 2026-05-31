# core/decision_logger.py
import uuid
import logging
from core.dependencies import get_session
from core.models import AgentDecision

logger = logging.getLogger("core_decision_logger")

def log_decision(workspace_id, agent_name: str, action: str, decision_status: str, reason: str, campaign_id=None, metadata: dict = None):
    """
    Logs business decisions strictly into the agent_decisions database table.
    Ensures fail-safe execution so that logging issues never crash the main application.
    """
    with get_session() as db:
        try:
            ws_id = None
            if workspace_id:
                if isinstance(workspace_id, uuid.UUID):
                    ws_id = workspace_id
                else:
                    ws_id = uuid.UUID(str(workspace_id))
            
            c_id = None
            if campaign_id:
                if isinstance(campaign_id, uuid.UUID):
                    c_id = campaign_id
                else:
                    c_id = uuid.UUID(str(campaign_id))
                    
            decision = AgentDecision(
                workspace_id=ws_id,
                campaign_id=c_id,
                agent_name=agent_name,
                action=action,
                decision_status=decision_status,
                reason=reason,
                meta_data=metadata or {}
            )
            db.add(decision)
            db.commit()
            logger.info(f"[AUDIT LOG] {agent_name} -> {action} ({decision_status})")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to write decision audit log: {e}", exc_info=True)