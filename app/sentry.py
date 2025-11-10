import os

import sentry_sdk
from dramatiq import get_broker
from sentry_sdk.integrations.dramatiq import DramatiqIntegration as _DramatiqIntegration
from sentry_sdk.integrations.dramatiq import SentryMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import app_settings


class DramatiqIntegration(_DramatiqIntegration):
    """
    Custom Dramatiq integration to set up Sentry middleware.

    The built-in one expects us to init Sentry before our broker, which is not
    practical in our case.
    """

    @staticmethod
    def setup_once() -> None:
        broker = get_broker()
        first_middleware = type(broker.middleware[0])
        broker.add_middleware(SentryMiddleware(), before=first_middleware)


# def configure_sentry() -> None:
#     sentry_sdk.init(
#         dsn=app_settings.SENTRY_DSN,
#         traces_sample_rate=0,
#         profiles_sample_rate=0,
#         release=os.environ.get("RELEASE_VERSION", "development"),
#         server_name=os.environ.get("RENDER_INSTANCE_ID", "localhost"),
#         environment=app_settings.ENV,
#         integrations=[
#             FastApiIntegration(transaction_style="endpoint"),
#             # DramatiqIntegration(),
#         ],
#     )
