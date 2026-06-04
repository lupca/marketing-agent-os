# core/celery_app.py
"""
Celery Application Instance cho Marketing Agent OS.
Broker: Redis | Backend: Redis

Queues:
  - rag_ingestion : Xử lý băm vector file mới upload
  - rag_cascade   : Cascade update tags/soft-delete đồng loạt chunks
"""
from celery import Celery
from config.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "marketing_agent",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["core.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Reliability
    task_acks_late=True,          # Ack sau khi task hoàn thành (tránh mất task khi worker crash)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1, # Không prefetch quá nhiều task (mỗi worker nhận 1 task)

    # Result expiry (1 giờ — đủ để UI poll)
    result_expires=3600,

    # Routing — tách 2 queue độc lập
    task_routes={
        "core.tasks.ingest_document":      {"queue": "rag_ingestion"},
        "core.tasks.cascade_update_tags":  {"queue": "rag_cascade"},
        "core.tasks.cascade_soft_delete":  {"queue": "rag_cascade"},
        "core.tasks.publish_to_social":    {"queue": "social_publisher"},
        "core.tasks.poll_video_agent_jobs": {"queue": "video_polling"},
        "core.tasks.sync_paid_campaign_metrics_task": {"queue": "orchestrator"},
        "core.tasks.state_orchestrator_cron": {"queue": "orchestrator"},
    },

    # Periodic tasks (Celery Beat schedule configuration)
    beat_schedule={
        "poll-video-agent-jobs-every-60s": {
            "task": "core.tasks.poll_video_agent_jobs",
            "schedule": 60.0,  # Run every 60 seconds
        },
        "sync-paid-campaign-metrics-every-30m": {
            "task": "core.tasks.sync_paid_campaign_metrics_task",
            "schedule": 1800.0,  # Run every 30 minutes
        },
        "state-orchestrator-cron-every-60s": {
            "task": "core.tasks.state_orchestrator_cron",
            "schedule": 60.0,  # Run every 60 seconds (Orchestrator ticks)
        },
    },

    # Retry policy mặc định cho tất cả tasks
    task_max_retries=3,
    task_default_retry_delay=30,  # 30 giây giữa các lần retry

    # Timezone
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
)

if __name__ == "__main__":
    celery_app.start()
