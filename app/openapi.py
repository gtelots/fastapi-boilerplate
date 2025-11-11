"""OpenAPI configuration."""

from enum import StrEnum
from typing import Any, NotRequired, TypedDict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.config import Environment, app_settings, image_settings
from app.kit.metadata import add_metadata_query_schema


class OpenAPIExternalDoc(TypedDict):
    description: NotRequired[str]
    url: str


class OpenAPITag(TypedDict):
    name: str
    description: NotRequired[str]
    externalDocs: NotRequired[dict[str, str]]


class APITag(StrEnum):
    """
    Tags used by our documentation to better organize the endpoints.

    They should be set after the "group" tag, which is used to group the endpoints
    in the generated documentation.

    **Example**

        ```py
        router = APIRouter(prefix="/products", tags=["products", APITag.public])
        ```
    """

    public = "public"
    private = "private"
    mcp = "mcp"

    @classmethod
    def metadata(cls) -> list[OpenAPITag]:
        return [
            {
                "name": cls.public,
                "description": (
                    "Endpoints shown and documented in the API documentation "
                    "and available in our SDKs."
                ),
            },
            {
                "name": cls.private,
                "description": (
                    "Endpoints that should appear in the schema only "
                    "in development to generate our internal JS SDK."
                ),
            },
            {
                "name": cls.mcp,
                "description": "Endpoints enabled in the MCP server.",
            },
        ]


class OpenAPIParameters(TypedDict):
    title: str
    summary: str
    version: str
    description: str
    docs_url: str | None
    redoc_url: str | None
    openapi_tags: list[dict[str, Any]]
    servers: list[dict[str, Any]] | None


OPENAPI_PARAMETERS: OpenAPIParameters = {
    "title": image_settings.TITLE,
    "version": image_settings.VERSION,
    "summary": image_settings.DESCRIPTION,
    "description": f"Read the docs at ${image_settings.DOCUMENTATION}",
    "debug": app_settings.DEBUG,
    "docs_url": None
    if app_settings.is_environment({Environment.SANDBOX, Environment.PRODUCTION})
    else "/docs",
    "redoc_url": None
    if app_settings.is_environment({Environment.SANDBOX, Environment.PRODUCTION})
    else "/redoc",
    "openapi_tags": APITag.metadata(),  # type: ignore
}


def set_openapi_generator(app: FastAPI) -> None:
    def _openapi_generator() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            webhooks=app.webhooks.routes,
            tags=app.openapi_tags,
            separate_input_output_schemas=app.separate_input_output_schemas,
        )

        openapi_schema = add_metadata_query_schema(openapi_schema)
        return openapi_schema

    app.openapi = _openapi_generator  # type: ignore[method-assign]


__all__ = [
    "OPENAPI_PARAMETERS",
    "APITag",
    "set_openapi_generator",
]
