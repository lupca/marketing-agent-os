#!/bin/bash
# start_workers.sh
# Script to start Celery worker and beat concurrently under Ubuntu

echo "Starting Celery Worker..."
python3 -m celery -A core.celery_app worker --loglevel=info --concurrency=2 -Q rag_ingestion,rag_cascade,video_polling,social_publisher &
WORKER_PID=$!

echo "Starting Celery Beat..."
python3 -m celery -A core.celery_app beat --loglevel=info &
BEAT_PID=$!

# Handle shutdown cleanly on Ctrl+C
cleanup() {
    echo ""
    echo "Stopping Celery Worker (PID $WORKER_PID)..."
    kill $WORKER_PID 2>/dev/null
    echo "Stopping Celery Beat (PID $BEAT_PID)..."
    kill $BEAT_PID 2>/dev/null
    echo "All workers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "--------------------------------------------------------"
echo "Workers started successfully!"
echo "Worker PID: $WORKER_PID"
echo "Beat PID: $BEAT_PID"
echo "Press Ctrl+C to stop both."
echo "--------------------------------------------------------"

# Wait for background processes to keep log output active
wait $WORKER_PID $BEAT_PID
