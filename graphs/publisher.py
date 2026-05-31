# graphs/publisher.py
import logging
import uuid
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.models import PlatformVariant, MasterContent, Workspace, MarketingCampaign
from core.decision_logger import log_decision
from graphs.state import AgencyState

logger = logging.getLogger("graphs_publisher")
logging.basicConfig(level=logging.INFO)

def publisher_node(state: AgencyState) -> dict:
    """
    Publisher Node (Ban Sáng Tạo).
    Executes after Sếp click '[Duyệt và Đăng]'. Saves variant to database.
    """
    logger.info("CEO Approved! Publishing kịch bản to PostgreSQL database...")
    
    db: Session = SessionLocal()
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    product_id = state.get("product_id")
    variants = state.get("variants", [])
    master_data = state.get("master_content", {})
    
    try:
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        ws_id = ws.id if ws else uuid.UUID(str(workspace_id))
        
        # Resolve campaign_id NOT NULL constraint
        if not campaign_id:
            # Create a default campaign dynamically
            new_camp = MarketingCampaign(
                workspace_id=ws_id,
                product_id=uuid.UUID(str(product_id)) if product_id else None,
                name=f"Chiến dịch tự động {uuid.uuid4().hex[:6]}",
                status="active",
                budget=2000000.0
            )
            db.add(new_camp)
            db.commit()
            db.refresh(new_camp)
            campaign_id = str(new_camp.id)
            logger.info(f"Dynamically created campaign ID {campaign_id} for NOT NULL constraint.")
            
        # Save master content
        master = MasterContent(
            workspace_id=ws_id,
            campaign_id=uuid.UUID(str(campaign_id)),
            core_message=master_data.get("core_message", ""),
            approval_status="approved",
            meta_data=master_data
        )
        db.add(master)
        db.commit()
        
        # Save variants
        pvs = []
        for v in variants:
            pv = PlatformVariant(
                workspace_id=ws_id,
                master_content_id=master.id,
                platform=v.get("platform", "facebook"),
                adapted_copy=v.get("adapted_copy", ""),
                publish_status="scheduled", # Scheduled for publishing
                content_type="text",
                meta_data=v
            )
            db.add(pv)
            pvs.append(pv)
        db.commit()
        logger.info("Successfully persisted published campaign contents in database!")

        # Trigger background publishing tasks (CTO Design - section 2.4)
        from core.celery_app import celery_app
        for pv in pvs:
            try:
                celery_app.send_task(
                    "core.tasks.publish_to_social",
                    args=[str(pv.id)],
                    queue="social_publisher"
                )
                logger.info(f"Triggered background publishing job for variant_id: {pv.id}")
            except Exception as broker_err:
                logger.error(f"Failed to dispatch Celery task to broker for variant {pv.id}: {broker_err}")
                try:
                    # Update variant status to failed locally since task could not be sent
                    pv.publish_status = 'failed'
                    meta = dict(pv.meta_data) if pv.meta_data else {}
                    meta["error_message"] = f"Failed to dispatch background job (Broker Connection Refused): {broker_err}"
                    pv.meta_data = meta
                    db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to update variant status after broker error: {db_err}")
        
        # Log publisher decision
        log_decision(
            workspace_id=ws_id,
            campaign_id=campaign_id,
            agent_name="Publisher Node",
            action="Approve & Publish",
            decision_status="success",
            reason=f"Duyệt và xuất bản thành công kịch bản. Lên lịch đăng {len(variants)} kịch bản chuyển đổi lên mạng xã hội.",
            metadata={"variants_count": len(variants), "master_content": master_data.get("core_message", "")}
        )
    except Exception as e:
        logger.error(f"Error saving published contents: {e}")
    finally:
        db.close()
        
    return {"sop_stage": "execution"}

def waiting_approval_barrier_node(state: AgencyState) -> dict:
    """A barrier node where LangGraph will pause (interrupt_before) awaiting human approval."""
    logger.info("LangGraph paused at approval barrier. Awaiting Sếp approval...")
    return {"sop_stage": "waiting_approval"}

def route_after_guardian(state: AgencyState) -> str:
    """
    Conditional routing from Brand Guardian (Scoring Gatekeeper).
    Routes to approval barrier or Copywriter node.
    """
    stage = state.get("sop_stage")
    logs = state.get("feedback_log", [])
    
    # Check if maximum review loops exceeded (Max 3 loops to avoid infinite cycle)
    if len(logs) >= 3:
        logger.warning("Max rewrite iterations (3) reached! Automatically passing to CEO review with warning.")
        return "waiting_approval_barrier"
        
    if stage == "waiting_approval":
        return "waiting_approval_barrier"
        
    # Return to Copywriter for revisions
    logger.warning("Feedback rewrite triggered! Routing back to Copywriter Node.")
    return "copywriter"
