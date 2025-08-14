import pytest
from types import SimpleNamespace

from inventory_api.services import product_service
from inventory_api.models.product import VersionedProductIdentifier
from inventory_api.crud.cosmos_serialization import normalize_category


@pytest.mark.asyncio
async def test_create_product_normalizes_category_and_converts_decimal(
    monkeypatch, container, product_create_model
):
    called = {}

    async def fake_create_product(container, item):
        # ensure category is normalized and price converted to float
        assert item["category"] == normalize_category("Gadgets")
        assert isinstance(item["price"], float)
        called["ok"] = True
        # Return a DB-like dict
        return {
            **item,
            "id": "abc",
            "_etag": '"etag"',
            "last_updated": "2025-01-01T00:00:00Z",
            "_rid": "rid",
            "_self": "self",
            "_attachments": "attachments",
            "_ts": 1714761600,
        }

    monkeypatch.setattr(
        product_service, "crud", SimpleNamespace(create_product=fake_create_product)
    )

    res = await product_service.create_product(container, product_create_model)
    assert called.get("ok") is True
    assert res.id == "abc"


@pytest.mark.asyncio
async def test_update_product_builds_patch_operations(
    monkeypatch, container, product_update_model
):
    identifier = VersionedProductIdentifier(
        id="abc", category="Gadgets", _etag='"etag"'
    )

    async def fake_update_product(
        container, identifier, patch_operations, if_match=None
    ):
        # ensure patch operation for price exists and if_match is provided
        assert any(p.get("path") == "/price" for p in patch_operations)
        assert if_match == identifier.etag
        # Return a DB-like dict with updated price
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

    monkeypatch.setattr(
        product_service, "crud", SimpleNamespace(update_product=fake_update_product)
    )

    res = await product_service.update_product(
        container, identifier, product_update_model
    )
    assert res.id == "abc"
    assert float(res.price) == 12.5
