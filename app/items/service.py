"""Item service layer."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, UnaryExpression, asc, desc, or_, select
from sqlalchemy.exc import IntegrityError

from app.exceptions import HttpRequestValidationError, ValidationError
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

        Raises:
            HttpRequestValidationError: If validation fails (e.g., duplicate SKU)
        """
        # Validate SKU uniqueness if provided
        if item_create.sku:
            await self._validate_sku_unique(session, item_create.sku)

        # Validate business rules
        await self._validate_item_create(item_create)

        item = Item(**item_create.model_dump())
        session.add(item)

        try:
            await session.flush()
            await session.refresh(item)
        except IntegrityError as e:
            await session.rollback()

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

        Raises:
            HttpRequestValidationError: If validation fails
        """
        update_data = item_update.model_dump(exclude_unset=True)

        # Validate SKU uniqueness if being updated
        if "sku" in update_data and update_data["sku"] is not None:
            await self._validate_sku_unique(session, update_data["sku"], exclude_id=item.id)

        # Validate business rules for update
        await self._validate_item_update(item, item_update)

        for attr, value in update_data.items():
            setattr(item, attr, value)

        item.set_modified_at()
        session.add(item)

        try:
            await session.flush()
            await session.refresh(item)
        except IntegrityError as e:
            await session.rollback()

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

    async def _validate_sku_unique(
        self,
        session: AsyncSession,
        sku: str,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        """
        Validate that SKU is unique.

        Args:
            session: Database session
            sku: SKU to validate
            exclude_id: Optional item ID to exclude from uniqueness check (for updates)

        Raises:
            HttpRequestValidationError: If SKU already exists
        """
        statement = select(Item).where(
            Item.sku == sku,
            Item.deleted_at.is_(None),
        )

        if exclude_id:
            statement = statement.where(Item.id != exclude_id)

        result = await session.execute(statement)
        existing_item = result.scalar_one_or_none()

        if existing_item:
            raise HttpRequestValidationError([
                ValidationError(
                    loc=("body", "sku"),
                    msg=f"SKU '{sku}' already exists",
                    type="value_error.duplicate",
                    input=sku,
                )
            ])

    async def _validate_item_create(self, item_create: ItemCreate) -> None:
        """
        Validate business rules for item creation.

        Args:
            item_create: Item creation data

        Raises:
            HttpRequestValidationError: If validation fails
        """
        errors: list[ValidationError] = []

        # Example: Validate price is reasonable (not too high)
        if item_create.price > 100_000_000:  # 1 million dollars in cents
            errors.append(
                ValidationError(
                    loc=("body", "price"),
                    msg="Price is too high. Maximum allowed is $1,000,000",
                    type="value_error.too_high",
                    input=item_create.price,
                )
            )

        # Example: Validate quantity is reasonable
        if item_create.quantity > 1_000_000:
            errors.append(
                ValidationError(
                    loc=("body", "quantity"),
                    msg="Quantity is too high. Maximum allowed is 1,000,000",
                    type="value_error.too_high",
                    input=item_create.quantity,
                )
            )

        if errors:
            raise HttpRequestValidationError(errors)

    async def _validate_item_update(self, item: Item, item_update: ItemUpdate) -> None:
        """
        Validate business rules for item update.

        Args:
            item: Existing item
            item_update: Update data

        Raises:
            HttpRequestValidationError: If validation fails
        """
        errors: list[ValidationError] = []
        update_data = item_update.model_dump(exclude_unset=True)

        # Validate price if being updated
        if "price" in update_data:
            price = update_data["price"]
            if price is not None and price > 100_000_000:
                errors.append(
                    ValidationError(
                        loc=("body", "price"),
                        msg="Price is too high. Maximum allowed is $1,000,000",
                        type="value_error.too_high",
                        input=price,
                    )
                )

        # Validate quantity if being updated
        if "quantity" in update_data:
            quantity = update_data["quantity"]
            if quantity is not None and quantity > 1_000_000:
                errors.append(
                    ValidationError(
                        loc=("body", "quantity"),
                        msg="Quantity is too high. Maximum allowed is 1,000,000",
                        type="value_error.too_high",
                        input=quantity,
                    )
                )

        if errors:
            raise HttpRequestValidationError(errors)


# Create a singleton instance
item_service = ItemService()

