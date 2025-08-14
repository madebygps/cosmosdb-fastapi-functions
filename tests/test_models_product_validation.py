import pytest
from decimal import Decimal
from pydantic import ValidationError

from inventory_api.models.product import ProductCreate, ProductUpdate


def test_product_update_requires_at_least_one_field():
    with pytest.raises(ValidationError):
        # No fields provided should raise due to model_validator
        # use model_validate to avoid static analyzer complaints about missing ctor args
        ProductUpdate.model_validate({})


def test_product_create_rejects_negative_price():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Bad",
            description="d",
            category="Gadgets",
            price=Decimal("-1.00"),
            sku="BAD-1",
            quantity=1,
        )


def test_product_create_rejects_invalid_sku_pattern():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Bad",
            description="d",
            category="Gadgets",
            price=Decimal("1.00"),
            sku="bad lowercase",
            quantity=1,
        )


def test_product_create_rejects_more_than_two_decimal_places():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Bad",
            description="d",
            category="Gadgets",
            price=Decimal("1.234"),
            sku="BAD-2",
            quantity=1,
        )
