"""Item Pydantic schemas."""

from typing import Annotated

from pydantic import Field

from app.kit.schemas import IDSchema, Schema, TimestampedSchema


class ItemBase(Schema):
    """Base schema for Item with common fields."""

    name: Annotated[
        str,
        Field(
            description="Name of the item.",
            min_length=1,
            max_length=255,
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            description="Optional description of the item.",
            default=None,
        ),
    ] = None
    price: Annotated[
        int,
        Field(
            description="Price of the item in cents.",
            ge=0,
        ),
    ]
    quantity: Annotated[
        int,
        Field(
            description="Available quantity of the item.",
            ge=0,
        ),
    ] = 0
    sku: Annotated[
        str | None,
        Field(
            description="Stock Keeping Unit (SKU) - unique identifier for the item.",
            max_length=100,
            default=None,
        ),
    ] = None


class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    pass


class ItemUpdate(Schema):
    """Schema for updating an existing item."""

    name: Annotated[
        str | None,
        Field(
            description="Name of the item.",
            min_length=1,
            max_length=255,
            default=None,
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="Optional description of the item.",
            default=None,
        ),
    ] = None
    price: Annotated[
        int | None,
        Field(
            description="Price of the item in cents.",
            ge=0,
            default=None,
        ),
    ] = None
    quantity: Annotated[
        int | None,
        Field(
            description="Available quantity of the item.",
            ge=0,
            default=None,
        ),
    ] = None
    sku: Annotated[
        str | None,
        Field(
            description="Stock Keeping Unit (SKU) - unique identifier for the item.",
            max_length=100,
            default=None,
        ),
    ] = None


class Item(ItemBase, IDSchema, TimestampedSchema):
    """Schema for Item response."""

    model_config = {"json_schema_mode_override": "serialization"}

