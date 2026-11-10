from celery import shared_task


@shared_task(name="common.health_ping")
def health_ping() -> str:
    """Minimal M0 Celery task used to verify worker execution."""
    return "pong"

