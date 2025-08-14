import pytest
from decimal import Decimal
from types import SimpleNamespace

from inventory_api.models.product import ProductCreate, ProductUpdate


@pytest.fixture
def container():
    # lightweight container stub for tests
    return SimpleNamespace()


@pytest.fixture
def product_create_model() -> ProductCreate:
    return ProductCreate(
        name="Tst",
        description="d",
        category="Gadgets",
        price=Decimal("9.99"),
        sku="TST-1",
        quantity=1,
    )


@pytest.fixture
def product_update_model() -> ProductUpdate:
    return ProductUpdate(
        name=None, description=None, price=Decimal("12.50"), quantity=None
    )
