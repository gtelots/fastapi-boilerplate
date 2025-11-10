from app.kit.routing import (
    AutoCommitAPIRoute,
    IncludedInSchemaAPIRoute,
    SpeakeasyGroupAPIRoute,
    SpeakeasyIgnoreAPIRoute,
    SpeakeasyMCPAPIRoute,
    SpeakeasyNameOverrideAPIRoute,
    SpeakeasyPaginationAPIRoute,
    get_api_router_class,
)


class APIRoute(
    AutoCommitAPIRoute,
    IncludedInSchemaAPIRoute,
    SpeakeasyIgnoreAPIRoute,
    SpeakeasyNameOverrideAPIRoute,
    SpeakeasyGroupAPIRoute,
    SpeakeasyMCPAPIRoute,
    SpeakeasyPaginationAPIRoute,
):
    pass


APIRouter = get_api_router_class(APIRoute)

__all__ = ["APIRouter"]
