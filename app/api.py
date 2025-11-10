"""API router configuration."""

from fastapi import APIRouter

# Import and include sub-routers
from app.items.endpoints import router as items_router

router = APIRouter(prefix="/v1", tags=["v1"])

router.include_router(items_router)

__all__ = ["router"]
