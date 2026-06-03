# graphs/autonomous/publisher.py
import logging
import uuid
from core.dependencies import get_session
from core import pipeline_tracker
from graphs.supervisor.state import AgencyState
from graphs.autonomous.telemetry import instrument_node

logger = logging.getLogger("autonomous_nodes")


@instrument_node("publisher")
def publisher_node(state: AgencyState) -> dict:
    """
    Publisher Node: Formulates platform variants, registers external Platform_Ad_IDs in ad_mapper,
    sends dynamic creatives to social accounts, and terminates the graph.

    Kill Switch Guard:
        Before making ANY Facebook API calls, this node checks ``pipeline_tracker.is_kill_switch_active()``.
        If the kill switch is active, all external API publishing is skipped entirely.
        The pipeline returns a clean completion state indicating the reason.
        Internal DB writes (PlatformVariant records) are still performed for audit.

    Execution Mode Guard:
        In 'shadow' mode (``state.get("_execution_mode") == "shadow"``), real Facebook API
        calls are also skipped even if the kill switch is not active.
    """
    logger.info("Executing Publisher Node...")
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    variants = state.get("generated_variants") or []
    execution_mode = state.get("_execution_mode", "shadow")

    # ── Kill Switch Guard ──────────────────────────────────────────────────
    if pipeline_tracker.is_kill_switch_active(workspace_id=workspace_id):
        logger.warning(
            "[KILL SWITCH] ⛔ Publisher blocked — kill switch is ACTIVE. "
            "Skipping all external Facebook API calls. Pipeline will still complete."
        )
        return {
            "sandbox_feedbacks": list(state.get("sandbox_feedbacks") or []) + [{
                "stage": "publisher",
                "blocked_by": "kill_switch",
                "reason": "Kill switch active — all external API publishing blocked by operator."
            }],
            "sop_stage": "completed",
            "_kill_switch_blocked": True,
        }

    # ── Publishing Flow ───────────────────────────
    from core.integrations.fb_client import (
        FacebookAccountDisabledError,
        init_facebook_client,
        batch_create_creatives,
        batch_create_ads
    )
    from core.db_services import save_publisher_state
    from core.decision_logger import log_decision

    with get_session() as db:
        try:
            ws_id = uuid.UUID(str(workspace_id))
            camp_uuid = uuid.UUID(str(campaign_id)) if campaign_id else uuid.UUID("00000000-0000-0000-0000-000000000001")
            
            # 1. Separate variants by platform
            fb_variants = [v for v in variants if v.get("platform", "facebook") == "facebook"]
            tiktok_variants = [v for v in variants if v.get("platform") == "tiktok"]
            
            ad_mappings = {}
            fb_account_id = "mock_publisher_account"
            
            # 2. Publish Facebook variants if any
            if fb_variants:
                # Resolve and initialize Facebook Client
                api, fb_account_id, use_real_fb = init_facebook_client(workspace_id, db, campaign_id=campaign_id)
                
                if execution_mode == "shadow":
                    logger.info("[SHADOW MODE] Overriding Facebook publishing to mock mode.")
                    use_real_fb = False

                if use_real_fb:
                    logger.info(f"Starting batch publishing of {len(fb_variants)} Facebook variants to Facebook Ads API...")
                    creative_responses = batch_create_creatives(api, fb_account_id, workspace_id, fb_variants)
                    ad_mappings.update(batch_create_ads(api, fb_account_id, camp_uuid, creative_responses, db))
                elif execution_mode == "shadow":
                    logger.info(f"Shadow mode active: {len(fb_variants)} Facebook variants skipped publishing.")
                else:
                    raise RuntimeError("Facebook real publishing is disabled but execution mode is not shadow.")
                        
            # 3. Publish TikTok variants if any (Mocked as requested)
            if tiktok_variants:
                logger.info(f"TikTok integration is mocked. Simulating publishing of {len(tiktok_variants)} variants.")
                for v in tiktok_variants:
                    v_id = v.get("variant_id") or v.get("id")
                    ad_mappings[v_id] = f"mock_tiktok_ad_{uuid.uuid4().hex[:6]}"
                
            # 4. Atomically persist state and mappings in database
            save_publisher_state(db, ws_id, camp_uuid, variants, ad_mappings, fb_account_id)
            
            reasons = []
            if fb_variants:
                reasons.append(f"{len(fb_variants)} Facebook variants published")
            if tiktok_variants:
                reasons.append(f"{len(tiktok_variants)} TikTok script variants published")
            reason_str = ", ".join(reasons) if reasons else "No variants to publish"
            
            log_decision(
                workspace_id=ws_id,
                agent_name="Publisher Node",
                action="Omnichannel Social Publishing",
                decision_status="success",
                reason=f"Successfully processed social publishing: {reason_str}.",
                campaign_id=camp_uuid
            )
            
        except FacebookAccountDisabledError as disabled_err:
            logger.error(f"Terminal account restricted exception caught: {disabled_err}. Rollback transaction...")
            db.rollback()
            
            feedbacks = list(state.get("sandbox_feedbacks") or [])
            feedbacks.append({
                "stage": "publisher",
                "error": "Account Disabled/Restricted",
                "reason": str(disabled_err)
            })
            
            log_decision(
                workspace_id=uuid.UUID(str(workspace_id)),
                agent_name="Publisher Node",
                action="Facebook Ads Publishing",
                decision_status="failed",
                reason=f"Account Disabled/Restricted during publishing: {disabled_err}",
                campaign_id=uuid.UUID(str(campaign_id)) if campaign_id else None
            )
            
            return {
                "sandbox_feedbacks": feedbacks,
                "sop_stage": "completed"
            }
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}. Performing rollback...")
            db.rollback()
            raise
            
    logger.info("Stateless execution loop finished! Releasing system resources.")
    result = {"sop_stage": "completed"}
    if execution_mode == "shadow":
        result["_shadow_mode"] = True

    return result
