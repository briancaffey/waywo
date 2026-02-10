from celery import Celery
from celery.signals import worker_process_init

from src.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Create Celery app instance
celery_app = Celery(
    "waywo",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="waywo",
    task_routes={
        "debug_task": {"queue": "waywo"},
        "process_waywo_posts": {"queue": "waywo"},
        "process_waywo_post": {"queue": "waywo"},
        "generate_video": {"queue": "waywo"},
    },
    # Store beat schedule file in celery-data directory with proper permissions
    beat_schedule_filename="/app/celery-data/celerybeat-schedule",
    # Import tasks module to register tasks with Celery
    imports=["src.worker.tasks", "src.worker.video_tasks"],
)

# Import beat schedule configuration
# This allows beat schedule to be defined in a separate file
from src.worker.beat import beat_schedule

# Apply beat schedule
celery_app.conf.beat_schedule = beat_schedule


@worker_process_init.connect
def init_worker_tracing(**kwargs):
    """Initialize tracing when a Celery worker process starts."""
    from src.tracing import init_tracing

    init_tracing(service_name="waywo-worker")


@celery_app.task(name="debug_task")
def debug_task():
    """
    Simple debug Celery task that logs a success message.
    """
    print("CeleryTask Completion success")
    return {"status": "success", "message": "CeleryTask Completion success"}
