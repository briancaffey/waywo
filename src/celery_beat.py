"""
Celery Beat configuration for scheduled tasks.

This file defines periodic tasks that will be executed by Celery Beat.
Add your scheduled tasks here using the beat_schedule dictionary.

Example format:
    beat_schedule = {
        'task-name': {
            'task': 'task_module.task_function',
            'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
        },
    }
"""

# Placeholder for Celery Beat scheduled tasks
# Currently no scheduled tasks are configured
beat_schedule = {}
