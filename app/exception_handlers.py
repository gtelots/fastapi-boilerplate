"""Custom exception handlers."""

from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config import app_settings
from app.exceptions import (
    HttpError,
    HttpRedirectionError,
    HttpRequestValidationError,
    ResourceNotModified,
)


async def http_exception_handler(request: Request, exc: HttpError) -> JSONResponse:
    print(type(exc).__name__)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "ERROR", "message": exc.message, "licence": "© GTEL Maps"},
        headers=exc.headers,
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError | HttpRequestValidationError
) -> JSONResponse:
    print(type(exc).__name__)
    return JSONResponse(
        status_code=422,
        content={"status": "ERROR", "message": jsonable_encoder(exc.errors()), "licence": "© GTEL Maps"},
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
