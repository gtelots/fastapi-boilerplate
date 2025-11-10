"""Item sorting configuration."""

from enum import StrEnum
from typing import Annotated

from fastapi import Depends

from app.kit.sorting import Sorting, SortingGetter


class ItemSortProperty(StrEnum):
    """Available properties for sorting items."""

    created_at = "created_at"
    name = "name"
    price = "price"
    quantity = "quantity"


ListSorting = Annotated[
    list[Sorting[ItemSortProperty]],
    Depends(SortingGetter(ItemSortProperty, ["-created_at"])),
]

