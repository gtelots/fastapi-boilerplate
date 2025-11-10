"""Item API endpoints."""

from typing import Annotated

from fastapi import Depends, Path, Query, status
from pydantic import UUID4

from app.exceptions import ResourceNotFound
from app.kit.pagination import ListResource, PaginationParamsQuery
from app.postgres import AsyncSession, get_db_session
from app.routing import APIRouter

from . import sorting
from .models import Item as ItemModel
from .schemas import Item, ItemCreate, ItemUpdate
from .service import item_service

router = APIRouter(prefix="/items", tags=["items"])


ItemID = Annotated[UUID4, Path(description="The item ID.")]
ItemNotFound = {
    "description": "Item not found.",
    "model": ResourceNotFound.schema(),
}


@router.get(
    "/",
    summary="List Items",
    response_model=ListResource[Item],
)
async def list_items(
    pagination: PaginationParamsQuery,
    sorting: sorting.ListSorting,
    query: str | None = Query(
        None,
        description="Search query to filter items by name or SKU.",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[Item]:
    """
    List all items with optional filtering, pagination, and sorting.

    - **query**: Optional search term to filter by name or SKU
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 10, max: 100)
    - **sort**: Sort by field (e.g., -created_at, name, price)
    """
    results, count = await item_service.list(
        session,
        query=query,
        pagination=pagination,
        sorting=sorting,
    )

    return ListResource.from_paginated_results(
        [Item.model_validate(result) for result in results],
        count,
        pagination,
    )


@router.get(
    "/{id}",
    summary="Get Item",
    response_model=Item,
    responses={404: ItemNotFound},
)
async def get_item(
    id: ItemID,
    session: AsyncSession = Depends(get_db_session),
) -> ItemModel:
    """
    Get a specific item by ID.

    Returns the item details including:
    - Name, description, price, quantity
    - SKU (if available)
    - Creation and modification timestamps
    """
    item = await item_service.get_by_id(session, id)

    if item is None:
        raise ResourceNotFound()

    return item


@router.post(
    "/",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create Item",
    responses={201: {"description": "Item created."}},
)
async def create_item(
    item_create: ItemCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ItemModel:
    """
    Create a new item.

    Required fields:
    - **name**: Item name (1-255 characters)
    - **price**: Price in cents (must be >= 0)

    Optional fields:
    - **description**: Item description
    - **quantity**: Available quantity (default: 0)
    - **sku**: Stock Keeping Unit (must be unique if provided)
    """
    return await item_service.create(session, item_create)


@router.patch(
    "/{id}",
    response_model=Item,
    summary="Update Item",
    responses={
        200: {"description": "Item updated."},
        404: ItemNotFound,
    },
)
async def update_item(
    id: ItemID,
    item_update: ItemUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> ItemModel:
    """
    Update an existing item.

    All fields are optional. Only provided fields will be updated:
    - **name**: Item name
    - **description**: Item description
    - **price**: Price in cents
    - **quantity**: Available quantity
    - **sku**: Stock Keeping Unit
    """
    item = await item_service.get_by_id(session, id)

    if item is None:
        raise ResourceNotFound()

    return await item_service.update(session, item, item_update)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Item",
    responses={
        204: {"description": "Item deleted."},
        404: ItemNotFound,
    },
)
async def delete_item(
    id: ItemID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete an item (soft delete).

    The item will be marked as deleted but not removed from the database.
    Deleted items will not appear in list or get operations.
    """
    item = await item_service.get_by_id(session, id)

    if item is None:
        raise ResourceNotFound()

    await item_service.delete(session, item)

