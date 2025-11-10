from app import tasks
from app.logfire import configure_logfire
from app.logging import configure as configure_logging
# from app.sentry import configure_sentry
from app.worker import broker

# configure_sentry()
configure_logfire("worker")
configure_logging(logfire=True)

__all__ = ["tasks", "broker"]
