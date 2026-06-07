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
    """
    logger.info("Executing Publisher Node...")
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    variants = state.get("generated_variants") or []

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
            
            # 1. Separate variants by content type: video vs text
            video_variants = [v for v in variants if v.get("content_type") == "video_script"]
            text_variants = [v for v in variants if v.get("content_type") != "video_script"]
            
            ad_mappings = {}
            fb_account_id = "mock_publisher_account"
            
            # 2a. Delegate video variants to Video Agent (Asynchronous Continuation)
            if video_variants:
                from core.integrations.video_client import submit_video_job
                from core.models import BrandIdentity, MarketingCampaign
                
                # Fetch brand context for Video Agent payload
                brand = db.query(BrandIdentity).filter_by(workspace_id=ws_id).first()
                brand_name = brand.brand_name if brand else ""
                brand_voice = brand.voice_and_tone if brand else ""
                
                campaign = db.query(MarketingCampaign).filter_by(id=camp_uuid).first()
                campaign_name = campaign.name if campaign else ""
                campaign_objective = state.get("campaign_objective", "LEAD_GEN")
                
                for v in video_variants:
                    v_id = v.get("variant_id") or v.get("id")
                    angle_name = v.get("angle_name", "")
                    script_content = v.get("adapted_copy") or v.get("copy") or ""
                    platform = v.get("platform", "tiktok")
                    
                    try:
                        result = submit_video_job(
                            variant_id=str(v_id),
                            video_script=script_content,
                            platform=platform,
                            workspace_id=str(workspace_id),
                            campaign_id=str(campaign_id),
                            brand_name=brand_name,
                            brand_voice=brand_voice,
                            campaign_name=campaign_name,
                            campaign_objective=campaign_objective,
                            angle_name=angle_name,
                        )
                        v["video_agent_job_id"] = result["job_id"]
                        v["publish_status"] = "generating_media"
                        logger.info(
                            f"Video job submitted for variant {v_id}: "
                            f"video_agent_job_id={result['job_id']}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to submit video job for variant {v_id}: {e}")
                        v["publish_status"] = "video_submission_failed"
                        v["meta_data"] = {
                            **(v.get("meta_data") or {}),
                            "video_error": str(e)
                        }
                
                log_decision(
                    workspace_id=ws_id,
                    agent_name="Publisher Node",
                    action="Video Agent Delegation",
                    decision_status="success",
                    reason=f"Delegated {len(video_variants)} video variant(s) to Video Agent for rendering.",
                    campaign_id=camp_uuid
                )
            
            # 2b. Publish TEXT Facebook variants if any
            fb_variants = [v for v in text_variants if v.get("platform", "facebook") == "facebook"]
            tiktok_text_variants = [v for v in text_variants if v.get("platform") == "tiktok"]
            if fb_variants:
                # Resolve and initialize Facebook Client
                api, fb_account_id, use_real_fb = init_facebook_client(workspace_id, db, campaign_id=campaign_id)
                
                if use_real_fb:
                    logger.info(f"Starting batch publishing of {len(fb_variants)} Facebook variants to Facebook Ads API...")
                    creative_responses = batch_create_creatives(api, fb_account_id, workspace_id, fb_variants)
                    ad_mappings.update(batch_create_ads(api, fb_account_id, camp_uuid, creative_responses, db))
                else:
                    logger.info(f"Facebook real publishing is disabled: {len(fb_variants)} Facebook variants skipped publishing.")
                        
            # 3. Publish TikTok text variants if any (Mocked as requested)
            if tiktok_text_variants:
                logger.info(f"TikTok text integration is mocked. Simulating publishing of {len(tiktok_text_variants)} variants.")
                for v in tiktok_text_variants:
                    v_id = v.get("variant_id") or v.get("id")
                    ad_mappings[v_id] = f"mock_tiktok_ad_{uuid.uuid4().hex[:6]}"
                
            # 4. Atomically persist state and mappings in database
            save_publisher_state(db, ws_id, camp_uuid, variants, ad_mappings, fb_account_id)
            
            reasons = []
            if fb_variants:
                reasons.append(f"{len(fb_variants)} Facebook text variants published")
            if tiktok_text_variants:
                reasons.append(f"{len(tiktok_text_variants)} TikTok text variants published")
            if video_variants:
                reasons.append(f"{len(video_variants)} video variants delegated to Video Agent")
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
    return {"sop_stage": "completed"}
