import pytest
from types import SimpleNamespace
from decimal import Decimal
from typing import cast

from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.core.exceptions import ServiceRequestError
from azure.cosmos.aio import ContainerProxy

from inventory_api.services import product_service
from inventory_api.exceptions import (
    ProductDuplicateSKUError,
    DatabaseConnectionError,
    PreconditionFailedError,
)
from inventory_api.models.product import (
    ProductCreate,
    ProductUpdate,
    VersionedProductIdentifier,
)


@pytest.mark.asyncio
async def test_create_duplicate_sku_raises_duplicate(monkeypatch):
    container = cast(ContainerProxy, SimpleNamespace())
    input_model = ProductCreate(
        name="Tst",
        description="d",
        category="Gadgets",
        price=Decimal("9.99"),
        sku="TST-1",
        quantity=1,
    )

    async def fake_create(container, item):
        # Simulate cosmos unique index conflict on SKU
        err = CosmosHttpResponseError(message="Unique index constraint /sku")
        err.status_code = 409
        raise err

    monkeypatch.setattr(product_service.crud, "create_product", fake_create)

    with pytest.raises(ProductDuplicateSKUError):
        await product_service.create_product(container, input_model)


@pytest.mark.asyncio
async def test_create_network_error_maps_to_db_connection(monkeypatch):
    container = cast(ContainerProxy, SimpleNamespace())
    input_model = ProductCreate(
        name="Tst",
        description="d",
        category="Gadgets",
        price=Decimal("9.99"),
        sku="TST-1",
        quantity=1,
    )

    async def fake_create(container, item):
        raise ServiceRequestError("nodename nor servname provided, or not known")

    monkeypatch.setattr(product_service.crud, "create_product", fake_create)

    with pytest.raises(DatabaseConnectionError):
        await product_service.create_product(container, input_model)


@pytest.mark.asyncio
async def test_update_precondition_failed(monkeypatch):
    container = cast(ContainerProxy, SimpleNamespace())
    identifier = VersionedProductIdentifier(
        id="abc", category="Gadgets", _etag='"etag"'
    )

    async def fake_update(container, identifier, patch_operations, if_match=None):
        # Simulate ETag failure by raising CosmosHttpResponseError with 412
        err = CosmosHttpResponseError(message="Precondition failed")
        err.status_code = 412
        raise err

    monkeypatch.setattr(product_service.crud, "update_product", fake_update)

    upd = ProductUpdate(
        name=None, description=None, price=Decimal("12.5"), quantity=None
    )

    with pytest.raises(PreconditionFailedError):
        await product_service.update_product(container, identifier, upd)
