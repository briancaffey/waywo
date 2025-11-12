import os
from celery import Celery

# Create Celery app instance
celery_app = Celery(
    "waywo",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
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
    },
)

# Import beat schedule configuration
# This allows beat schedule to be defined in a separate file
from src.celery_beat import beat_schedule

# Apply beat schedule
celery_app.conf.beat_schedule = beat_schedule


@celery_app.task(name="debug_task")
def debug_task():
    """
    Simple debug Celery task that logs a success message.
    """
    print("CeleryTask Completion success")
    return {"status": "success", "message": "CeleryTask Completion success"}
