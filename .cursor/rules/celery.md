# Celery Task Execution
- Always use `apply_async()` instead of `delay()` when calling Celery tasks
- This provides more control and is the recommended approach for async task execution

