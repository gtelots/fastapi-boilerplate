"""Tests for item endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from app.items.models import Item
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
class TestListItems:
    async def test_list_empty(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test listing items when database is empty."""
        response = await client.get("/api/items/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    async def test_list_items(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test listing multiple items."""
        await create_item(session, name="Item 1", sku="SKU-001")
        await create_item(session, name="Item 2", sku="SKU-002")
        await create_item(session, name="Item 3", sku="SKU-003")

        response = await client.get("/api/items/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["pagination"]["total"] == 3

    async def test_list_with_pagination(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test pagination parameters."""
        for i in range(5):
            await create_item(session, name=f"Item {i}", sku=f"SKU-{i:03d}")

        # First page
        response = await client.get("/api/items/?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pagination"]["total"] == 5

        # Second page
        response = await client.get("/api/items/?limit=2&offset=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pagination"]["total"] == 5

    async def test_list_with_search(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test search query parameter."""
        await create_item(session, name="Wireless Mouse", sku="WM-001")
        await create_item(session, name="Mechanical Keyboard", sku="MK-002")
        await create_item(session, name="Wireless Headset", sku="WH-003")

        response = await client.get("/api/items/?query=wireless")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pagination"]["total"] == 2

    async def test_list_with_sorting(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test sorting parameters."""
        await create_item(session, name="Zebra", price=3000, sku="Z-001")
        await create_item(session, name="Apple", price=1000, sku="A-001")
        await create_item(session, name="Mango", price=2000, sku="M-001")

        # Sort by name ascending
        response = await client.get("/api/items/?sort=name")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "Apple"
        assert data["items"][1]["name"] == "Mango"
        assert data["items"][2]["name"] == "Zebra"

        # Sort by price descending
        response = await client.get("/api/items/?sort=-price")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["price"] == 3000
        assert data["items"][1]["price"] == 2000
        assert data["items"][2]["price"] == 1000

    async def test_list_excludes_deleted(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that deleted items are excluded."""
        item1 = await create_item(session, name="Item 1", sku="SKU-001")
        await create_item(session, name="Item 2", sku="SKU-002")

        # Soft delete item1
        item1.set_deleted_at()
        session.add(item1)
        await session.flush()

        response = await client.get("/api/items/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Item 2"


@pytest.mark.asyncio
class TestGetItem:
    async def test_get_existing_item(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test getting an existing item."""
        item = await create_item(session, name="Test Item", sku="TEST-001")

        response = await client.get(f"/api/items/{item.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(item.id)
        assert data["name"] == "Test Item"
        assert data["sku"] == "TEST-001"

    async def test_get_nonexistent_item(self, client: AsyncClient) -> None:
        """Test getting a non-existent item returns 404."""
        random_id = uuid.uuid4()

        response = await client.get(f"/api/items/{random_id}")

        assert response.status_code == 404

    async def test_get_deleted_item(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test that deleted items return 404."""
        item = await create_item(session, name="Test Item", sku="TEST-001")

        # Soft delete the item
        item.set_deleted_at()
        session.add(item)
        await session.flush()

        response = await client.get(f"/api/items/{item.id}")

        assert response.status_code == 404

    async def test_get_invalid_uuid(self, client: AsyncClient) -> None:
        """Test getting item with invalid UUID format."""
        response = await client.get("/api/items/not-a-uuid")

        assert response.status_code == 422


@pytest.mark.asyncio
class TestCreateItem:
    async def test_create_basic_item(self, client: AsyncClient) -> None:
        """Test creating a basic item."""
        payload = {
            "name": "New Item",
            "description": "New description",
            "price": 1500,
            "quantity": 25,
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Item"
        assert data["description"] == "New description"
        assert data["price"] == 1500
        assert data["quantity"] == 25
        assert data["sku"] is None
        assert "id" in data
        assert "created_at" in data

    async def test_create_item_with_sku(self, client: AsyncClient) -> None:
        """Test creating an item with SKU."""
        payload = {
            "name": "New Item",
            "price": 1000,
            "quantity": 10,
            "sku": "NEW-SKU-001",
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "NEW-SKU-001"

    async def test_create_duplicate_sku(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test that creating item with duplicate SKU fails."""
        await create_item(session, name="Existing Item", sku="DUPLICATE-SKU")

        payload = {
            "name": "New Item",
            "price": 2000,
            "quantity": 20,
            "sku": "DUPLICATE-SKU",
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_create_missing_required_fields(self, client: AsyncClient) -> None:
        """Test that missing required fields returns 422."""
        payload = {
            "description": "Missing name and price",
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 422

    async def test_create_invalid_price(self, client: AsyncClient) -> None:
        """Test that negative price is rejected."""
        payload = {
            "name": "Invalid Item",
            "price": -100,
            "quantity": 10,
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 422

    async def test_create_price_too_high(self, client: AsyncClient) -> None:
        """Test that price over limit is rejected."""
        payload = {
            "name": "Expensive Item",
            "price": 200_000_000,
            "quantity": 1,
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 422

    async def test_create_quantity_too_high(self, client: AsyncClient) -> None:
        """Test that quantity over limit is rejected."""
        payload = {
            "name": "High Quantity Item",
            "price": 1000,
            "quantity": 2_000_000,
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 422

    async def test_create_name_too_long(self, client: AsyncClient) -> None:
        """Test that name over max length is rejected."""
        payload = {
            "name": "A" * 300,  # Over 255 character limit
            "price": 1000,
            "quantity": 10,
        }

        response = await client.post("/api/items/", json=payload)

        assert response.status_code == 422


@pytest.mark.asyncio
class TestUpdateItem:
    async def test_update_name(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test updating item name."""
        item = await create_item(session, name="Old Name", sku="TEST-001")

        payload = {"name": "New Name"}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["sku"] == "TEST-001"  # Unchanged

    async def test_update_price(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test updating item price."""
        item = await create_item(session, price=1000, sku="TEST-001")

        payload = {"price": 2000}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 2000

    async def test_update_quantity(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test updating item quantity."""
        item = await create_item(session, quantity=10, sku="TEST-001")

        payload = {"quantity": 50}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 50

    async def test_update_sku(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test updating item SKU."""
        item = await create_item(session, sku="OLD-SKU")

        payload = {"sku": "NEW-SKU"}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "NEW-SKU"

    async def test_update_multiple_fields(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test updating multiple fields at once."""
        item = await create_item(
            session,
            name="Old Name",
            price=1000,
            quantity=10,
            sku="OLD-SKU",
        )

        payload = {
            "name": "New Name",
            "price": 2000,
            "quantity": 20,
        }

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["price"] == 2000
        assert data["quantity"] == 20
        assert data["sku"] == "OLD-SKU"  # Not updated

    async def test_update_nonexistent_item(self, client: AsyncClient) -> None:
        """Test updating a non-existent item returns 404."""
        random_id = uuid.uuid4()

        payload = {"name": "New Name"}

        response = await client.patch(f"/api/items/{random_id}", json=payload)

        assert response.status_code == 404

    async def test_update_deleted_item(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test updating a deleted item returns 404."""
        item = await create_item(session, name="Test Item", sku="TEST-001")

        # Soft delete the item
        item.set_deleted_at()
        session.add(item)
        await session.flush()

        payload = {"name": "New Name"}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 404

    async def test_update_duplicate_sku(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test that updating to duplicate SKU fails."""
        await create_item(session, name="Item 1", sku="EXISTING-SKU")
        item2 = await create_item(session, name="Item 2", sku="OTHER-SKU")

        payload = {"sku": "EXISTING-SKU"}

        response = await client.patch(f"/api/items/{item2.id}", json=payload)

        assert response.status_code == 422

    async def test_update_price_too_high(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test that updating price over limit fails."""
        item = await create_item(session, price=1000, sku="TEST-001")

        payload = {"price": 200_000_000}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 422

    async def test_update_invalid_price(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test that negative price is rejected."""
        item = await create_item(session, price=1000, sku="TEST-001")

        payload = {"price": -100}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 422

    async def test_update_empty_payload(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test updating with empty payload."""
        item = await create_item(session, name="Test Item", sku="TEST-001")

        payload = {}

        response = await client.patch(f"/api/items/{item.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Item"  # Unchanged


@pytest.mark.asyncio
class TestDeleteItem:
    async def test_delete_item(self, client: AsyncClient, session: AsyncSession) -> None:
        """Test deleting an item."""
        item = await create_item(session, name="To Delete", sku="DELETE-001")

        response = await client.delete(f"/api/items/{item.id}")

        assert response.status_code == 204

        # Verify item is soft deleted
        get_response = await client.get(f"/api/items/{item.id}")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_item(self, client: AsyncClient) -> None:
        """Test deleting a non-existent item returns 404."""
        random_id = uuid.uuid4()

        response = await client.delete(f"/api/items/{random_id}")

        assert response.status_code == 404

    async def test_delete_already_deleted_item(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test deleting an already deleted item returns 404."""
        item = await create_item(session, name="Test Item", sku="TEST-001")

        # Soft delete the item
        item.set_deleted_at()
        session.add(item)
        await session.flush()

        response = await client.delete(f"/api/items/{item.id}")

        assert response.status_code == 404

    async def test_delete_item_not_in_list(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that deleted items don't appear in list."""
        item1 = await create_item(session, name="Item 1", sku="SKU-001")
        item2 = await create_item(session, name="Item 2", sku="SKU-002")

        response = await client.delete(f"/api/items/{item1.id}")

        assert response.status_code == 204

        # Verify only item2 appears in list
        list_response = await client.get("/api/items/")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(item2.id)

    async def test_delete_allows_sku_reuse(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Test that SKU can be reused after item is deleted."""
        item = await create_item(session, name="Item 1", sku="REUSABLE-SKU")

        # Delete the item
        response = await client.delete(f"/api/items/{item.id}")
        assert response.status_code == 204

        # Should be able to create new item with same SKU
        payload = {
            "name": "Item 2",
            "price": 2000,
            "quantity": 20,
            "sku": "REUSABLE-SKU",
        }

        create_response = await client.post("/api/items/", json=payload)

        assert create_response.status_code == 201
        data = create_response.json()
        assert data["sku"] == "REUSABLE-SKU"
        assert data["id"] != str(item.id)

