import pytest
from decimal import Decimal

from types import SimpleNamespace
from typing import cast

from azure.cosmos.aio import ContainerProxy

import inventory_api.services.product_service as product_service
from inventory_api.models.product import (
    ProductCreate,
    ProductUpdate,
    ProductIdentifier,
    VersionedProductIdentifier,
)


@pytest.mark.asyncio
async def test_create_product_creates_and_returns_product(monkeypatch):
    # Prepare
    container = cast(ContainerProxy, SimpleNamespace())
    input_model = ProductCreate(
        name="Tst",
        description="d",
        category="Gadgets",
        price=Decimal("9.99"),
        sku="TST-1",
        quantity=1,
    )

    created_db = {
        "name": "Tst",
        "description": "d",
        "category": "gadgets",
        "price": 9.99,
        "sku": "TST-1",
        "quantity": 1,
        "status": "active",
        "id": "abc",
        "_etag": '"etag"',
        "last_updated": "2025-01-01T00:00:00Z",
    }

    async def fake_create_product(container, item):
        assert item["name"] == "Tst"
        return created_db

    monkeypatch.setattr(product_service.crud, "create_product", fake_create_product)

    # Act
    res = await product_service.create_product(container, input_model)

    # Assert
    assert res.id == "abc"
    assert res.sku == "TST-1"


@pytest.mark.asyncio
async def test_update_product_patches_and_returns(monkeypatch):
    container = cast(ContainerProxy, SimpleNamespace())
    identifier = VersionedProductIdentifier(
        id="abc", category="Gadgets", _etag='"etag"'
    )
    upd = ProductUpdate(
        name=None, description=None, price=Decimal("12.5"), quantity=None
    )

    async def fake_update_product(
        container, identifier, patch_operations, if_match=None
    ):
        # ensure patch operation was built
        assert any(p.get("path") == "/price" for p in patch_operations)
        # Return a full product dict similar to what Cosmos would return after patch
        return {
            "name": "Tst",
            "description": "d",
            "category": "gadgets",
            "price": 12.5,
            "sku": "TST-1",
            "quantity": 1,
            "status": "active",
            "id": "abc",
            "_etag": '"etag2"',
            "last_updated": "2025-01-01T00:00:00Z",
            "_rid": "rid",
            "_self": "self",
            "_attachments": "attachments",
            "_ts": 1714761600,
        }

    monkeypatch.setattr(product_service.crud, "update_product", fake_update_product)

    res = await product_service.update_product(container, identifier, upd)
    assert res.id == "abc"
    assert float(res.price) == 12.5


@pytest.mark.asyncio
async def test_delete_product_calls_crud(monkeypatch):
    container = cast(ContainerProxy, SimpleNamespace())
    identifier = ProductIdentifier(id="abc", category="Gadgets")

    called = {}

    async def fake_delete_product(container, product_identifier):
        called["ok"] = True

    monkeypatch.setattr(product_service.crud, "delete_product", fake_delete_product)

    await product_service.delete_product(container, identifier)
    assert called.get("ok") is True
