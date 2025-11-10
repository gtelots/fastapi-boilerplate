from typing import Annotated
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from fastapi import Depends, Query
from safe_redirect_url import url_has_allowed_host_and_scheme

from app.config import app_settings


def get_safe_return_url(return_to: str | None) -> str:
    # Unsafe URL -> fallback to default
    if return_to is None or not url_has_allowed_host_and_scheme(
        return_to, app_settings.ALLOWED_HOSTS
    ):
        return app_settings.generate_frontend_url(app_settings.FRONTEND_DEFAULT_RETURN_PATH)

    # For paths, ensure we have an absolute URL on the frontend
    url_info = urlparse(return_to)
    if not url_info.netloc:
        return app_settings.generate_frontend_url(return_to)

    return return_to


async def _get_safe_return_url_dependency(return_to: str | None = Query(None)) -> str:
    return get_safe_return_url(return_to)


ReturnTo = Annotated[str, Depends(_get_safe_return_url_dependency)]


def add_query_parameters(url: str, **kwargs: str | list[str]) -> str:
    scheme, netloc, path, params, query, fragment = urlparse(url)
    parsed_query = parse_qs(query)
    return urlunparse(
        (
            scheme,
            netloc,
            path,
            params,
            urlencode({**parsed_query, **kwargs}, doseq=True),
            fragment,
        )
    )
