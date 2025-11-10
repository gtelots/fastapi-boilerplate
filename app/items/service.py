"""Item service layer."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, UnaryExpression, asc, desc, or_, select

from app.kit.pagination import PaginationParams, paginate
from app.kit.sorting import Sorting
from app.postgres import AsyncSession

from .models import Item
from .schemas import ItemCreate, ItemUpdate
from .sorting import ItemSortProperty


class ItemService:
    """Service for managing items."""

    async def list(
        self,
        session: AsyncSession,
        *,
        query: str | None = None,
        pagination: PaginationParams,
        sorting: list[Sorting[ItemSortProperty]] = [(ItemSortProperty.created_at, True)],
    ) -> tuple[Sequence[Item], int]:
        """
        List items with optional filtering, pagination, and sorting.

        Args:
            session: Database session
            query: Optional search query to filter by name or SKU
            pagination: Pagination parameters
            sorting: List of sorting criteria

        Returns:
            Tuple of (items, total_count)
        """
        statement = select(Item).where(Item.deleted_at.is_(None))

        # Apply search filter
        if query is not None:
            statement = statement.where(
                or_(
                    Item.name.ilike(f"%{query}%"),
                    Item.sku.ilike(f"%{query}%") if Item.sku.isnot(None) else False,
                )
            )

        # Apply sorting
        statement = self._apply_sorting(statement, sorting)

        # Apply pagination
        results, count = await paginate(session, statement, pagination=pagination)

        return results, count

    async def get_by_id(
        self,
        session: AsyncSession,
        item_id: uuid.UUID,
    ) -> Item | None:
        """
        Get an item by ID.

        Args:
            session: Database session
            item_id: Item ID

        Returns:
            Item if found, None otherwise
        """
        statement = select(Item).where(
            Item.id == item_id,
            Item.deleted_at.is_(None),
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        item_create: ItemCreate,
    ) -> Item:
        """
        Create a new item.

        Args:
            session: Database session
            item_create: Item creation data

        Returns:
            Created item
        """
        item = Item(**item_create.model_dump())
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item

    async def update(
        self,
        session: AsyncSession,
        item: Item,
        item_update: ItemUpdate,
    ) -> Item:
        """
        Update an existing item.

        Args:
            session: Database session
            item: Item to update
            item_update: Update data

        Returns:
            Updated item
        """
        for attr, value in item_update.model_dump(exclude_unset=True).items():
            setattr(item, attr, value)

        item.set_modified_at()
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item

    async def delete(
        self,
        session: AsyncSession,
        item: Item,
    ) -> None:
        """
        Soft delete an item.

        Args:
            session: Database session
            item: Item to delete
        """
        item.set_deleted_at()
        session.add(item)
        await session.flush()

    def _apply_sorting(
        self,
        statement: Select[tuple[Item]],
        sorting: list[Sorting[ItemSortProperty]],
    ) -> Select[tuple[Item]]:
        """Apply sorting to the query."""
        order_by_clauses: list[UnaryExpression[bool]] = []

        for sort_property, is_desc in sorting:
            column = getattr(Item, sort_property.value)
            order_by_clauses.append(desc(column) if is_desc else asc(column))

        if order_by_clauses:
            statement = statement.order_by(*order_by_clauses)

        return statement


# Create a singleton instance
item_service = ItemService()

