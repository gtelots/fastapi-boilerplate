"""Tests for item service layer."""

import uuid

import pytest

from app.exceptions import HttpRequestValidationError
from app.items.models import Item
from app.items.schemas import ItemCreate, ItemUpdate
from app.items.service import item_service
from app.items.sorting import ItemSortProperty
from app.kit.pagination import PaginationParams
from app.postgres import AsyncSession


async def create_item(
    session: AsyncSession,
    *,
    name: str = "Test Item",
    description: str | None = "Test description",
    price: int = 1000,
    quantity: int = 10,
    sku: str | None = None,
) -> Item:
    """Helper function to create an item for testing."""
    item = Item(
        name=name,
        description=description,
        price=price,
        quantity=quantity,
        sku=sku,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


@pytest.mark.asyncio
class TestList:
    async def test_empty_list(self, session: AsyncSession) -> None:
        """Test listing items when database is empty."""
        items, count = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=10),
        )

        assert len(items) == 0
        assert count == 0

    async def test_list_items(self, session: AsyncSession) -> None:
        """Test listing multiple items."""
        # Create test items
        await create_item(session, name="Item 1", sku="SKU-001")
        await create_item(session, name="Item 2", sku="SKU-002")
        await create_item(session, name="Item 3", sku="SKU-003")

        items, count = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=10),
        )

        assert len(items) == 3
        assert count == 3

    async def test_list_with_pagination(self, session: AsyncSession) -> None:
        """Test pagination works correctly."""
        # Create 5 items
        for i in range(5):
            await create_item(session, name=f"Item {i}", sku=f"SKU-{i:03d}")

        # Get first page
        items, count = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=2),
        )

        assert len(items) == 2
        assert count == 5

        # Get second page
        items, count = await item_service.list(
            session,
            pagination=PaginationParams(page=2, limit=2),
        )

        assert len(items) == 2
        assert count == 5

    async def test_list_with_search(self, session: AsyncSession) -> None:
        """Test search filtering by name."""
        await create_item(session, name="Wireless Mouse", sku="WM-001")
        await create_item(session, name="Mechanical Keyboard", sku="MK-002")
        await create_item(session, name="Wireless Headset", sku="WH-003")

        # Search by name
        items, count = await item_service.list(
            session,
            query="wireless",
            pagination=PaginationParams(page=1, limit=10),
        )

        assert len(items) == 2
        assert count == 2
        assert all("wireless" in item.name.lower() for item in items)

    async def test_list_with_sku_search(self, session: AsyncSession) -> None:
        """Test search filtering by SKU."""
        await create_item(session, name="Item 1", sku="WM-001")
        await create_item(session, name="Item 2", sku="MK-002")
        await create_item(session, name="Item 3", sku="WH-003")

        # Search by SKU
        items, count = await item_service.list(
            session,
            query="MK",
            pagination=PaginationParams(page=1, limit=10),
        )

        assert len(items) == 1
        assert count == 1
        assert items[0].sku == "MK-002"

    async def test_list_excludes_deleted(self, session: AsyncSession) -> None:
        """Test that deleted items are excluded from list."""
        item1 = await create_item(session, name="Item 1", sku="SKU-001")
        await create_item(session, name="Item 2", sku="SKU-002")

        # Soft delete item1
        item1.set_deleted_at()
        session.add(item1)
        await session.flush()

        items, count = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=10),
        )

        assert len(items) == 1
        assert count == 1
        assert items[0].name == "Item 2"

    async def test_list_with_sorting(self, session: AsyncSession) -> None:
        """Test sorting by different properties."""
        await create_item(session, name="Zebra", price=3000, sku="Z-001")
        await create_item(session, name="Apple", price=1000, sku="A-001")
        await create_item(session, name="Mango", price=2000, sku="M-001")

        # Sort by name ascending
        items, _ = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=10),
            sorting=[(ItemSortProperty.name, False)],
        )

        assert items[0].name == "Apple"
        assert items[1].name == "Mango"
        assert items[2].name == "Zebra"

        # Sort by price descending
        items, _ = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=10),
            sorting=[(ItemSortProperty.price, True)],
        )

        assert items[0].price == 3000
        assert items[1].price == 2000
        assert items[2].price == 1000


@pytest.mark.asyncio
class TestGetById:
    async def test_get_existing_item(self, session: AsyncSession) -> None:
        """Test getting an existing item by ID."""
        created_item = await create_item(session, name="Test Item", sku="TEST-001")

        item = await item_service.get_by_id(session, created_item.id)

        assert item is not None
        assert item.id == created_item.id
        assert item.name == "Test Item"

    async def test_get_nonexistent_item(self, session: AsyncSession) -> None:
        """Test getting a non-existent item returns None."""
        random_id = uuid.uuid4()

        item = await item_service.get_by_id(session, random_id)

        assert item is None

    async def test_get_deleted_item(self, session: AsyncSession) -> None:
        """Test that deleted items are not returned."""
        created_item = await create_item(session, name="Test Item", sku="TEST-001")

        # Soft delete the item
        created_item.set_deleted_at()
        session.add(created_item)
        await session.flush()

        item = await item_service.get_by_id(session, created_item.id)

        assert item is None


@pytest.mark.asyncio
class TestCreate:
    async def test_create_basic_item(self, session: AsyncSession) -> None:
        """Test creating a basic item."""
        item_create = ItemCreate(
            name="Test Item",
            description="Test description",
            price=1000,
            quantity=10,
        )

        item = await item_service.create(session, item_create)

        assert item.id is not None
        assert item.name == "Test Item"
        assert item.description == "Test description"
        assert item.price == 1000
        assert item.quantity == 10
        assert item.sku is None
        assert item.created_at is not None

    async def test_create_item_with_sku(self, session: AsyncSession) -> None:
        """Test creating an item with SKU."""
        item_create = ItemCreate(
            name="Test Item",
            price=1000,
            quantity=10,
            sku="TEST-SKU-001",
        )

        item = await item_service.create(session, item_create)

        assert item.sku == "TEST-SKU-001"

    async def test_create_duplicate_sku(self, session: AsyncSession) -> None:
        """Test that creating an item with duplicate SKU fails."""
        # Create first item
        await create_item(session, name="Item 1", sku="DUPLICATE-SKU")

        # Try to create second item with same SKU
        item_create = ItemCreate(
            name="Item 2",
            price=2000,
            quantity=20,
            sku="DUPLICATE-SKU",
        )

        with pytest.raises(HttpRequestValidationError) as exc_info:
            await item_service.create(session, item_create)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "sku")
        assert "already exists" in errors[0].msg

    async def test_create_price_too_high(self, session: AsyncSession) -> None:
        """Test that creating an item with price too high fails."""
        item_create = ItemCreate(
            name="Expensive Item",
            price=200_000_000,  # Over the limit
            quantity=1,
        )

        with pytest.raises(HttpRequestValidationError) as exc_info:
            await item_service.create(session, item_create)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "price")
        assert "too high" in errors[0].msg

    async def test_create_quantity_too_high(self, session: AsyncSession) -> None:
        """Test that creating an item with quantity too high fails."""
        item_create = ItemCreate(
            name="High Quantity Item",
            price=1000,
            quantity=2_000_000,  # Over the limit
        )

        with pytest.raises(HttpRequestValidationError) as exc_info:
            await item_service.create(session, item_create)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "quantity")
        assert "too high" in errors[0].msg


@pytest.mark.asyncio
class TestUpdate:
    async def test_update_name(self, session: AsyncSession) -> None:
        """Test updating item name."""
        item = await create_item(session, name="Old Name", sku="TEST-001")

        item_update = ItemUpdate(name="New Name")
        updated_item = await item_service.update(session, item, item_update)

        assert updated_item.name == "New Name"
        assert updated_item.modified_at is not None

    async def test_update_price(self, session: AsyncSession) -> None:
        """Test updating item price."""
        item = await create_item(session, price=1000, sku="TEST-001")

        item_update = ItemUpdate(price=2000)
        updated_item = await item_service.update(session, item, item_update)

        assert updated_item.price == 2000

    async def test_update_quantity(self, session: AsyncSession) -> None:
        """Test updating item quantity."""
        item = await create_item(session, quantity=10, sku="TEST-001")

        item_update = ItemUpdate(quantity=20)
        updated_item = await item_service.update(session, item, item_update)

        assert updated_item.quantity == 20

    async def test_update_sku(self, session: AsyncSession) -> None:
        """Test updating item SKU."""
        item = await create_item(session, sku="OLD-SKU")

        item_update = ItemUpdate(sku="NEW-SKU")
        updated_item = await item_service.update(session, item, item_update)

        assert updated_item.sku == "NEW-SKU"

    async def test_update_sku_duplicate(self, session: AsyncSession) -> None:
        """Test that updating to duplicate SKU fails."""
        await create_item(session, name="Item 1", sku="EXISTING-SKU")
        item2 = await create_item(session, name="Item 2", sku="OTHER-SKU")

        item_update = ItemUpdate(sku="EXISTING-SKU")

        with pytest.raises(HttpRequestValidationError) as exc_info:
            await item_service.update(session, item2, item_update)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "sku")
        assert "already exists" in errors[0].msg

    async def test_update_price_too_high(self, session: AsyncSession) -> None:
        """Test that updating price too high fails."""
        item = await create_item(session, price=1000, sku="TEST-001")

        item_update = ItemUpdate(price=200_000_000)

        with pytest.raises(HttpRequestValidationError) as exc_info:
            await item_service.update(session, item, item_update)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "price")
        assert "too high" in errors[0].msg

    async def test_update_quantity_too_high(self, session: AsyncSession) -> None:
        """Test that updating quantity too high fails."""
        item = await create_item(session, quantity=10, sku="TEST-001")

        item_update = ItemUpdate(quantity=2_000_000)

        with pytest.raises(HttpRequestValidationError) as exc_info:
            await item_service.update(session, item, item_update)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "quantity")
        assert "too high" in errors[0].msg

    async def test_update_multiple_fields(self, session: AsyncSession) -> None:
        """Test updating multiple fields at once."""
        item = await create_item(
            session,
            name="Old Name",
            price=1000,
            quantity=10,
            sku="OLD-SKU",
        )

        item_update = ItemUpdate(
            name="New Name",
            price=2000,
            quantity=20,
        )
        updated_item = await item_service.update(session, item, item_update)

        assert updated_item.name == "New Name"
        assert updated_item.price == 2000
        assert updated_item.quantity == 20
        assert updated_item.sku == "OLD-SKU"  # Not updated

    async def test_update_partial(self, session: AsyncSession) -> None:
        """Test partial update only changes specified fields."""
        item = await create_item(
            session,
            name="Original Name",
            price=1000,
            quantity=10,
            sku="TEST-SKU",
        )

        item_update = ItemUpdate(price=2000)
        updated_item = await item_service.update(session, item, item_update)

        assert updated_item.name == "Original Name"  # Unchanged
        assert updated_item.price == 2000  # Changed
        assert updated_item.quantity == 10  # Unchanged
        assert updated_item.sku == "TEST-SKU"  # Unchanged


@pytest.mark.asyncio
class TestDelete:
    async def test_delete_item(self, session: AsyncSession) -> None:
        """Test soft deleting an item."""
        item = await create_item(session, name="To Delete", sku="DELETE-001")

        await item_service.delete(session, item)

        # Item should be soft deleted
        assert item.deleted_at is not None

        # Item should not be returned by get_by_id
        retrieved_item = await item_service.get_by_id(session, item.id)
        assert retrieved_item is None

    async def test_delete_item_not_in_list(self, session: AsyncSession) -> None:
        """Test that deleted items don't appear in list."""
        item1 = await create_item(session, name="Item 1", sku="SKU-001")
        item2 = await create_item(session, name="Item 2", sku="SKU-002")

        await item_service.delete(session, item1)

        items, count = await item_service.list(
            session,
            pagination=PaginationParams(page=1, limit=10),
        )

        assert len(items) == 1
        assert count == 1
        assert items[0].id == item2.id

    async def test_delete_allows_sku_reuse(self, session: AsyncSession) -> None:
        """Test that SKU can be reused after item is deleted."""
        item1 = await create_item(session, name="Item 1", sku="REUSABLE-SKU")

        # Delete the item
        await item_service.delete(session, item1)

        # Should be able to create new item with same SKU
        item_create = ItemCreate(
            name="Item 2",
            price=2000,
            quantity=20,
            sku="REUSABLE-SKU",
        )

        item2 = await item_service.create(session, item_create)

        assert item2.sku == "REUSABLE-SKU"
        assert item2.id != item1.id

