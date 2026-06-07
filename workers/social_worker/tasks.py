import logging
import tempfile
import os
import uuid
import requests
from datetime import datetime, timedelta
from core.celery_app import celery_app
from core.dependencies import get_session
from core.models import PlatformVariant, MediaAsset, SocialInteraction
from core.ai_clients import UploadPostAuthError, UploadPostValidationError, UploadPostRateLimitError, UploadPostServerError
from core.decision_logger import log_decision
from core.storage import download_file_from_minio
from core.document_service import process_and_store_document

from workers.social_worker.native_publisher import publish_via_native_api
from workers.social_worker.thirdparty_publisher import publish_via_upload_post

logger = logging.getLogger("social_worker_tasks")

# ============================================================
# TASK 4: Social Media Publisher Background Job (CTO Design)
# ============================================================
@celery_app.task(
    bind=True,
    name="workers.social_worker.tasks.publish_to_social",
    queue="social_publisher",
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def publish_to_social(self, variant_id: str):
    """
    Background job to publish a PlatformVariant to social media.
    Dispatches to Native FB API or 3rd Party (Upload-Post API) service.
    """
    tmp_files = []
    platform = "unknown"
    
    with get_session() as db:
        try:
            logger.info(f"[publish_to_social] START variant_id={variant_id}")
        
            # 1. Fetch variant data from DB (with UUID format validation)
            try:
                variant_uuid = uuid.UUID(variant_id)
            except ValueError as val_err:
                logger.error(f"[publish_to_social] Invalid variant_id UUID format: {variant_id}")
                raise UploadPostValidationError(f"Invalid variant_id UUID format: {variant_id}")
            
            variant = db.query(PlatformVariant).filter_by(id=variant_uuid).first()
            if not variant:
                logger.error(f"[publish_to_social] Variant {variant_id} not found in database!")
                return {"status": "error", "message": "Variant not found"}
            
            platform = variant.platform
        
            # 2. Idempotency Check
            if variant.publish_status == 'published':
                logger.info(f"[publish_to_social] Variant {variant_id} is already published. Skipping.")
                return {"status": "skipped", "message": "Already published"}
            
            # 3. Retrieve Credentials from Workspace Integration configs (or environment variables)
            from core.utils import get_integration_config
            configs_post = get_integration_config(variant.workspace_id, "upload-post")
            configs_pos = get_integration_config(variant.workspace_id, "upload-pos")
            integration_configs = {**configs_pos, **configs_post}
            
            api_key = integration_configs.get("api_key")
            is_upload_post_active = bool(api_key and api_key != "dummy_key")
            if not is_upload_post_active and platform != "facebook":
                raise UploadPostAuthError("UPLOAD_POST_API_KEY is not configured and native fallback is only supported for facebook.")
            
            user = integration_configs.get("user") or "topvnsport"
            config_fb_page_id = integration_configs.get("facebook_page_id")
        
            # 4. Prepare parameters
            title = variant.adapted_copy or ""
        
            # 5. Dynamic Facebook Page Resolution
            fb_page_id = None
            if platform == "facebook":
                if config_fb_page_id:
                    fb_page_id = config_fb_page_id
                    logger.info(f"[publish_to_social] Using configured Facebook page ID: {fb_page_id} from integrations.")
                else:
                    try:
                        if is_upload_post_active:
                            headers = {"Authorization": f"Apikey {api_key}"}
                            response = requests.get("https://api.upload-post.com/api/uploadposts/facebook/pages", headers=headers, timeout=20)
                            if response.status_code == 200:
                                pages_data = response.json()
                                pages = pages_data.get("pages", [])
                                for p in pages:
                                    name = p.get("name", "").lower()
                                    if "top vn sport" in name or "topvnsport" in name:
                                        fb_page_id = p.get("id")
                                        logger.info(f"[publish_to_social] Resolved Facebook page ID: {fb_page_id} for name: {p.get('name')}")
                                        break
                        else:
                            from core.models import SocialAccount
                            account = db.query(SocialAccount).filter_by(workspace_id=variant.workspace_id, platform='facebook').first()
                            if account and account.access_token:
                                response = requests.get("https://graph.facebook.com/v19.0/me", params={"access_token": account.access_token}, timeout=20)
                                if response.status_code == 200:
                                    fb_page_id = response.json().get("id")
                                    logger.info(f"[publish_to_social] Resolved Facebook page ID: {fb_page_id} from Native API")
                    except Exception as e:
                        logger.warning(f"[publish_to_social] Failed to dynamically query Facebook pages: {e}")
                    
                    if not fb_page_id:
                        raise UploadPostValidationError("facebook_page_id is not configured for Facebook platform. Please set it in Workspace Integrations.")

            # Determine publishing format using Content Format / Type
            content_format = variant.content_type or "text"
            if isinstance(variant.meta_data, dict):
                content_format = variant.meta_data.get("content_type") or variant.meta_data.get("content_format") or content_format
            
            content_format = content_format.lower()
        
            # 6. Gather and download media assets if any
            photos = []
            is_video_post = "video" in content_format or "script" in content_format
        
            if variant.platform_media_ids:
                for asset_id in variant.platform_media_ids:
                    asset = db.query(MediaAsset).filter_by(id=uuid.UUID(str(asset_id))).first()
                    if asset:
                        if asset.file_type == "video":
                            is_video_post = True
                        # Download file from MinIO/Local storage to temporary path
                        ext = os.path.splitext(asset.file_key)[-1] or (".mp4" if asset.file_type == "video" else ".jpg")
                        tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
                        os.close(tmp_fd) # Close file descriptor
                    
                        logger.info(f"[publish_to_social] Downloading asset {asset_id} to temporary path: {tmp_path}")
                        download_file_from_minio(asset.file_key, tmp_path)
                        photos.append(tmp_path)
                        tmp_files.append(tmp_path)
                    
            # 7. Execute Call to Native API or Upload-Post API based on config
            if platform == "facebook" and not is_upload_post_active:
                api_res = publish_via_native_api(
                    db=db,
                    variant=variant,
                    fb_page_id=fb_page_id,
                    title=title,
                    is_video_post=is_video_post,
                    photos=photos
                )
            else:
                api_res = publish_via_upload_post(
                    api_key=api_key,
                    user=user,
                    platform=platform,
                    fb_page_id=fb_page_id,
                    title=title,
                    is_video_post=is_video_post,
                    photos=photos
                )
            
            logger.info(f"[publish_to_social] API Response: {api_res}")
        
            # 8. Success: Update variant status in DB
            from sqlalchemy.sql import func
            variant.publish_status = 'published'
            variant.published_at = func.now()
        
            # If the API returned a post ID or job ID, store it in meta_data and platform_post_id
            post_id = None
            if isinstance(api_res, dict):
                results = api_res.get("results") or {}
                if platform in results:
                    post_id = results.get(platform, {}).get("post_id")
            if not post_id:
                post_id = api_res.get("post_id") or api_res.get("request_id")
            if post_id:
                variant.platform_post_id = str(post_id)
            
            # Update meta_data with API result (Idempotency/Observability)
            meta = dict(variant.meta_data) if variant.meta_data else {}
            meta["api_response"] = api_res
            if "job_id" in api_res:
                meta["api_job_id"] = api_res["job_id"]
            variant.meta_data = meta
            db.commit()
        
            # Log success decision (Observability)
            log_decision(
                workspace_id=variant.workspace_id,
                agent_name="Social Publisher Worker",
                action="API Publish Success",
                decision_status="success",
                reason=f"Đăng tải kịch bản thành công lên {platform.upper()} via API.",
                campaign_id=None,
                metadata={"variant_id": variant_id, "api_response": api_res}
            )
        
            return {"status": "success", "variant_id": variant_id, "api_response": api_res}
        
        except (UploadPostAuthError, UploadPostValidationError) as err:
            # Permanent Fails -> DO NOT RETRY
            logger.error(f"[publish_to_social] Permanent Failure for variant {variant_id}: {err}", exc_info=True)
            db.rollback()
            try:
                variant_uuid = uuid.UUID(variant_id)
                variant = db.query(PlatformVariant).filter_by(id=variant_uuid).first()
            except ValueError:
                variant = None
            if variant:
                variant.publish_status = 'failed'
                meta = dict(variant.meta_data) if variant.meta_data else {}
                meta["error_message"] = str(err)
                variant.meta_data = meta
                db.commit()
            
                # Log permanent failure (Observability)
                log_decision(
                    workspace_id=variant.workspace_id,
                    agent_name="Social Publisher Worker",
                    action="API Publish Failed (Permanent)",
                    decision_status="failed",
                    reason=f"Thất bại vĩnh viễn khi đăng lên {platform.upper()}: {err}",
                    campaign_id=None,
                    metadata={"variant_id": variant_id, "error": str(err)}
                )
            return {"status": "failed", "error": str(err)}
        
        except Exception as exc:
            # Transient Failure -> Retry with backoff
            logger.warning(f"[publish_to_social] Transient Failure for variant {variant_id}, retrying: {exc}", exc_info=True)
            db.rollback()
        
            backoff_time = self.default_retry_delay * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=backoff_time)
        
        finally:
            # Clean up temporary media files to prevent memory/disk leak
            for filepath in tmp_files:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logger.info(f"[publish_to_social] Deleted temporary file: {filepath}")
                    except Exception as cleanup_err:
                        logger.warning(f"[publish_to_social] Failed to delete temporary file {filepath}: {cleanup_err}")

# ============================================================
# TASK 5: Own Media Analytics Sync Job (CTO Design)
# ============================================================
@celery_app.task(
    bind=True,
    name="workers.social_worker.tasks.sync_own_media_metrics",
    queue="social_publisher",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def sync_own_media_metrics(self):
    """
    Background job to fetch post analytics for all organically published variants.
    """
    with get_session() as db:
        try:
            logger.info("[sync_own_media_metrics] STARTing sync job.")
            api_key = os.getenv("UPLOAD_POST_API_KEY")
            if not api_key:
                raise UploadPostAuthError("UPLOAD_POST_API_KEY is not configured in environment variables.")        
            headers = {"Authorization": f"Apikey {api_key}"}
        
            # 1. Tracking Job: Fetch published variants within last 7 days that have a platform_post_id
            seven_days_ago = datetime.now() - timedelta(days=7)
            variants = db.query(PlatformVariant).filter(
                PlatformVariant.publish_status == 'published',
                PlatformVariant.platform_post_id.isnot(None),
                PlatformVariant.published_at >= seven_days_ago
            ).all()
        
            logger.info(f"[sync_own_media_metrics] Found {len(variants)} published variants to sync.")
        
            for variant in variants:
                platform = variant.platform
                post_id = variant.platform_post_id
                user = "topvnsport"
            
                # GET /api/uploadposts/post-analytics
                url = f"https://api.upload-post.com/api/uploadposts/post-analytics?platform_post_id={post_id}&platform={platform}&user={user}"
                try:
                    res = requests.get(url, headers=headers, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        metrics = data.get("platforms", {}).get(platform, {}).get("post_metrics", {})
                        if metrics:
                            variant.metric_views = metrics.get("views", variant.metric_views)
                            variant.metric_likes = metrics.get("likes", variant.metric_likes)
                            variant.metric_comments = metrics.get("comments", variant.metric_comments)
                            variant.metric_shares = metrics.get("shares", variant.metric_shares)
                            logger.info(f"[sync_own_media_metrics] Updated metrics for variant {variant.id}")
                except Exception as e:
                    logger.warning(f"[sync_own_media_metrics] Failed to fetch analytics for variant {variant.id}: {e}")

                # Listening Job (Instagram First): GET /api/uploadposts/comments
                if platform == 'instagram':
                    comments_url = f"https://api.upload-post.com/api/uploadposts/comments?media_id={post_id}&user={user}"
                    try:
                        c_res = requests.get(comments_url, headers=headers, timeout=20)
                        if c_res.status_code == 200:
                            c_data = c_res.json()
                            comments = c_data.get("comments", [])
                        
                            # Process negative comments for Self-Feedback Loop
                            negative_comments = []
                            for c in comments:
                                c_id = c.get("id")
                                text = c.get("text", "")
                                existing = db.query(SocialInteraction).filter_by(platform_user_id=c_id).first()
                                if not existing:
                                    interaction = SocialInteraction(
                                        workspace_id=variant.workspace_id,
                                        variant_id=variant.id,
                                        platform_user_id=c_id,
                                        content=text,
                                        sentiment="neutral"
                                    )
                                    db.add(interaction)
                                    # Simple keyword matching for MVP
                                    lower_text = text.lower()
                                    if any(word in lower_text for word in ["mờ", "chán", "nhảm", "đắt", "tệ", "xấu", "lỗi", "chê"]):
                                        interaction.sentiment = "negative"
                                        negative_comments.append(text)
                                    
                            # Self-Learning (Self-Feedback Job): Push to RAG
                            if negative_comments:
                                feedback_text = f"Bài học rút ra (Anti-pattern) từ các bình luận tiêu cực cho chiến dịch '{variant.platform}':\n"
                                for nc in negative_comments:
                                    feedback_text += f"- Khách hàng phản hồi: '{nc}'\n"
                                feedback_text += "Hãy tránh lặp lại văn phong hoặc nội dung gây ra phản ứng này."
                            
                                try:
                                    process_and_store_document(
                                        db=db,
                                        workspace_id=str(variant.workspace_id),
                                        file_bytes=feedback_text.encode('utf-8'),
                                        file_name=f"self_feedback_{variant.id}.md",
                                        access_tags=["self_feedback"]
                                    )
                                    logger.info(f"[sync_own_media_metrics] Added self-feedback to RAG for variant {variant.id}")
                                except Exception as rag_err:
                                    logger.warning(f"[sync_own_media_metrics] RAG ingestion failed for self-feedback: {rag_err}")
                    except Exception as e:
                        logger.warning(f"[sync_own_media_metrics] Failed to fetch comments for variant {variant.id}: {e}")
                    
            db.commit()
            logger.info("[sync_own_media_metrics] FINISHED sync job.")
            return {"status": "success", "synced_variants": len(variants)}
        except Exception as exc:
            logger.error(f"[sync_own_media_metrics] Failed: {exc}")
            db.rollback()
            raise self.retry(exc=exc)
