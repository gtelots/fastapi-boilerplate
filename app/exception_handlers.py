"""Custom exception handlers."""

from urllib.parse import urlencode

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config import app_settings
from app.logging import Logger
from app.kit.validation_formatting import generate_validation_error
from app.exceptions import (
    HttpError,
    HttpRedirectionError,
    HttpRequestValidationError,
    ResourceNotModified,
)

log: Logger = structlog.get_logger(__name__)


async def http_exception_handler(request: Request, exc: HttpError) -> JSONResponse:
    log.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    error_content = {
        "status": "ERROR",
        "message": exc.message,
        "licence": "© GTEL Maps",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content,
        headers=exc.headers,
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError | HttpRequestValidationError
) -> JSONResponse:
    log.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    error_content = {
        "status": "ERROR",
        "message": "Validation Error",
        "error": generate_validation_error(exc),
        "licence": "© GTEL Maps",
    }
    return JSONResponse(
        status_code=422,
        content=error_content,
    )


async def http_redirection_exception_handler(
    request: Request, exc: HttpRedirectionError
) -> RedirectResponse:
    error_url_params = urlencode(
        {
            "message": exc.message,
            "return_to": exc.return_to or app_settings.FRONTEND_DEFAULT_RETURN_PATH,
        }
    )
    error_url = f"{app_settings.generate_frontend_url('/error')}?{error_url_params}"
    return RedirectResponse(error_url, 303)


async def http_not_modified_handler(
    request: Request, exc: ResourceNotModified
) -> Response:
    return Response(status_code=exc.status_code)


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        HttpRedirectionError,
        http_redirection_exception_handler,  # type: ignore
    )
    app.add_exception_handler(
        ResourceNotModified,
        http_not_modified_handler,  # type: ignore
    )

    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,  # type: ignore
    )
    app.add_exception_handler(
        HttpRequestValidationError,
        request_validation_exception_handler,  # type: ignore
    )
    app.add_exception_handler(
        HttpError,
        http_exception_handler, # type: ignore
    )
