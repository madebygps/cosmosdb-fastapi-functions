"""Service layer for product business logic.

Prepares data for DB operations and converts DB results into response models.
"""

from datetime import datetime, timezone
import uuid


from azure.cosmos.aio import ContainerProxy

from inventory_api.crud.cosmos_serialization import (
    normalize_category,
    prepare_decimals_for_cosmos_db,
)
from inventory_api.crud import product_crud as crud
from inventory_api.exceptions import handle_cosmos_error
from inventory_api.models.product import (
    ProductCreate,
    ProductIdentifier,
    ProductResponse,
    ProductUpdate,
    VersionedProductIdentifier,
    ProductStatus,
)


async def create_product(
    container: ContainerProxy, product: ProductCreate
) -> ProductResponse:
    data = product.model_dump()
    data["id"] = str(uuid.uuid4())
    data["status"] = ProductStatus.ACTIVE.value
    data["last_updated"] = datetime.now(timezone.utc).isoformat()

    data["category"] = normalize_category(data["category"])
    data = prepare_decimals_for_cosmos_db(data)

    try:
        db_result = await crud.create_product(container=container, item=data)
        return ProductResponse.model_validate(db_result)
    except Exception as e:
        # Reuse exception translation
        handle_cosmos_error(
            e, operation="create", sku=data.get("sku"), product_name=data.get("name")
        )
        raise


async def get_product_by_id(
    container: ContainerProxy, identifier: ProductIdentifier
) -> ProductResponse:
    identifier.category = normalize_category(identifier.category)
    db_item = await crud.get_product_by_id(container=container, product=identifier)
    return ProductResponse.model_validate(db_item)


async def update_product(
    container: ContainerProxy,
    identifier: VersionedProductIdentifier,
    updates: ProductUpdate,
) -> ProductResponse:
    update_dict = updates.model_dump(exclude_unset=True)
    update_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
    update_dict = prepare_decimals_for_cosmos_db(update_dict)

    patch_operations = []
    for key, value in update_dict.items():
        if key not in ["id", "category", "_etag"]:
            patch_operations.append({"op": "set", "path": f"/{key}", "value": value})

    identifier.category = normalize_category(identifier.category)

    try:
        db_result = await crud.update_product(
            container=container,
            identifier=identifier,
            patch_operations=patch_operations,
            if_match=identifier.etag,
        )
        return ProductResponse.model_validate(db_result)
    except Exception as e:
        handle_cosmos_error(
            e,
            operation="update",
            product_id=identifier.id,
            category=identifier.category,
        )
        raise


async def delete_product(
    container: ContainerProxy, product_identifier: ProductIdentifier
) -> None:
    product_identifier.category = normalize_category(product_identifier.category)
    try:
        await crud.delete_product(
            container=container, product_identifier=product_identifier
        )
    except Exception as e:
        handle_cosmos_error(
            e,
            operation="delete",
            product_id=product_identifier.id,
            category=product_identifier.category,
        )
        raise
