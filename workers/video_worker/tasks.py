import logging
from datetime import datetime
import uuid
from core.celery_app import celery_app
from core.dependencies import get_session
from core.integrations.video_client import get_job_status
from core.models import PlatformVariant, MediaAsset

logger = logging.getLogger("video_worker_tasks")

@celery_app.task(
    name="workers.video_worker.tasks.poll_video_agent_jobs",
    queue="video_polling",
)
def poll_video_agent_jobs():
    """
    Celery Beat task — chạy định kỳ.
    Quét PlatformVariant có publish_status="generating_media",
    poll Video Agent API, và trigger publish khi video sẵn sàng.
    """
    with get_session() as db:
        pending_variants = db.query(PlatformVariant).filter(
            PlatformVariant.publish_status == "generating_media"
        ).all()
        
        for variant in pending_variants:
            job_id = (variant.meta_data or {}).get("video_agent_job_id")
            if not job_id:
                continue
                
            try:
                status = get_job_status(job_id)
                
                if status["status"] == "COMPLETED" and status["result_url"]:
                    file_url = status["result_url"]
                    file_key = file_url.split("video-output/")[-1] if "video-output/" in file_url else f"job_{job_id}/final.mp4"
                    
                    # Create MediaAsset representing the rendered video
                    media_asset = MediaAsset(
                        id=uuid.uuid4(),
                        workspace_id=variant.workspace_id,
                        file_key=file_key,
                        file_url=file_url,
                        file_type="video",
                        aspect_ratio="9:16",
                        tags=["video_agent", "rendered"]
                    )
                    db.add(media_asset)
                    db.flush()
                    
                    # Assign the MediaAsset UUID to the variant's platform_media_ids list
                    variant.platform_media_ids = [media_asset.id]
                    variant.publish_status = "ready_to_publish"
                    variant.meta_data = {
                        **(variant.meta_data or {}),
                        "video_completed_at": datetime.utcnow().isoformat(),
                    }
                    db.commit()
                    
                    # Trigger social publishing (updated path to social worker dispatcher)
                    celery_app.send_task(
                        "workers.social_worker.tasks.publish_to_social",
                        args=[str(variant.id)],
                        queue="social_publisher",
                    )
                    logger.info(f"Video ready! Triggered publish for variant {variant.id}")
                    
                elif status["status"] == "FAILED":
                    variant.publish_status = "video_generation_failed"
                    variant.meta_data = {
                        **(variant.meta_data or {}),
                        "video_error": status.get("error", "Unknown error"),
                    }
                    db.commit()
                    logger.error(f"Video generation FAILED for variant {variant.id}")
                    
                else:
                    # Still processing — log progress
                    logger.info(
                        f"Video job {job_id} for variant {variant.id}: "
                        f"{status['status']} ({status['progress']}%)"
                    )
            except Exception as e:
                logger.error(f"Error polling video job {job_id}: {e}")
