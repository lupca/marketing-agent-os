import logging
import uuid
import asyncio
from datetime import datetime
from core.celery_app import celery_app
from core.dependencies import get_session
from core.models import PlatformVariant, CampaignAnalytics, MasterContent, Workspace, MarketingCampaign
from core.integrations.fb_client import fetch_campaign_metrics
from core.bandit_orchestrator import trigger_autonomous_generation

logger = logging.getLogger("orchestrator_worker_tasks")

# ============================================================
# TASK 6: Paid Campaign Metrics Sync & Soft-Delete
# ============================================================
@celery_app.task(name="workers.orchestrator_worker.tasks.sync_paid_campaign_metrics_task")
def sync_paid_campaign_metrics_task():
    with get_session() as db:
        variants = db.query(PlatformVariant).filter(
            PlatformVariant.is_active == True,
            PlatformVariant.publish_status == 'published'
        ).all()
        
        for variant in variants:
            try:
                # We assume platform_post_id holds the Meta ad_id or campaign_id for paid ads
                metrics = fetch_campaign_metrics(variant.platform_post_id)
                # If success, insert into campaign_analytics
                master = db.query(MasterContent).filter_by(id=variant.master_content_id).first()
                if master and master.campaign_id:
                    analytics = CampaignAnalytics(
                        campaign_id=master.campaign_id,
                        platform=variant.platform,
                        impressions=metrics.get('impressions', 0),
                        clicks=metrics.get('clicks', 0),
                        spend=metrics.get('spend', 0.0),
                        conversions=metrics.get('conversions', 0)
                    )
                    db.add(analytics)
                variant.sync_status = "synced"
            except Exception as e:
                error_str = str(e)
                # Meta API commonly returns HTTP 400 subcode 100 or DEL for deleted objects
                if "100" in error_str or "Does Not Exist" in error_str or "DEL" in error_str:
                    logger.warning(f"[SOFT DELETE] Variant {variant.id} returned API error: {e}. Deactivating.")
                    variant.is_active = False
                    variant.sync_status = "failed_deleted"
                else:
                    logger.error(f"Sync failed for variant {variant.id}: {e}")
                    variant.sync_status = "failed"
        db.commit()


# ============================================================
# TASK 7: Master Orchestrator Cronjob (Dynamic State Machine)
# ============================================================
@celery_app.task(name="workers.orchestrator_worker.tasks.state_orchestrator_cron")
def state_orchestrator_cron():
    with get_session() as db:
        workspaces = db.query(Workspace).all()
        for ws in workspaces:
            settings = ws.settings or {}
            
            # Count Active
            count_active = db.query(PlatformVariant).filter(
                PlatformVariant.workspace_id == ws.id,
                PlatformVariant.is_active == True
            ).count()
            
            logger.info(f"[ORCHESTRATOR] Workspace {ws.id} - Active Variants: {count_active}")
            
            MAX_LIMIT = settings.get("orchestrator_max_active_limit", 5)
            
            # Find an active campaign to trigger (heuristic)
            camp = db.query(MarketingCampaign).filter(
                MarketingCampaign.workspace_id == ws.id,
                MarketingCampaign.status == "active"
            ).first()
            if not camp:
                continue
                
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if count_active == 0:
                logger.info(f"[IGNITION PROTOCOL] Triggering 100% Explore for Workspace {ws.id}")
                # Force Explore & Generator
                loop.run_until_complete(
                    trigger_autonomous_generation(
                        workspace_id=str(ws.id),
                        campaign_id=str(camp.id),
                        product_id=str(camp.product_id),
                        db=db,
                        epsilon_override=1.0,
                        skip_generation=False
                    )
                )
            elif count_active > MAX_LIMIT:
                logger.info(f"[DARWIN PRUNING] Triggering 100% Exploit for Workspace {ws.id}")
                # Force Exploit & Skip Gen
                loop.run_until_complete(
                    trigger_autonomous_generation(
                        workspace_id=str(ws.id),
                        campaign_id=str(camp.id),
                        product_id=str(camp.product_id),
                        db=db,
                        epsilon_override=0.0,
                        skip_generation=True
                    )
                )
            else:
                logger.info(f"[BALANCED MAB] Normal operations for Workspace {ws.id}")
                loop.run_until_complete(
                    trigger_autonomous_generation(
                        workspace_id=str(ws.id),
                        campaign_id=str(camp.id),
                        product_id=str(camp.product_id),
                        db=db
                    )
                )
