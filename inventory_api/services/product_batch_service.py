"""Service layer for batch product business logic."""

from collections import defaultdict
from typing import Any
from datetime import datetime, timezone
import uuid

from azure.cosmos.aio import ContainerProxy

from inventory_api.crud import product_crud_batch as crud
from inventory_api.crud.cosmos_serialization import (
    normalize_category,
    prepare_decimals_for_cosmos_db,
)
from inventory_api.exceptions import handle_batch_operation_error
from inventory_api.models.product import (
    ProductBatchCreate,
    ProductBatchUpdate,
    ProductBatchDelete,
    ProductCreate,
    ProductResponse,
    ProductStatus,
)


async def create_products(
    container: ContainerProxy, batch_create: ProductBatchCreate
) -> list[ProductResponse]:
    if not batch_create.items:
        return []

    products_by_category: dict[str, list[ProductCreate]] = defaultdict(list)
    for product_model in batch_create.items:
        products_by_category[normalize_category(product_model.category)].append(
            product_model
        )

    async def process_category_creates(
        category_pk: str, product_list_for_category: list[ProductCreate]
    ):
        batch_operations_for_db: list[tuple] = []

        for product_to_create in product_list_for_category:
            data = product_to_create.model_dump()
            data["id"] = str(uuid.uuid4())
            data["status"] = ProductStatus.ACTIVE.value
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            data["category"] = normalize_category(data["category"])
            data = prepare_decimals_for_cosmos_db(data)
            batch_operations_for_db.append(("create", (data,), {}))

        if not batch_operations_for_db:
            return []

        try:
            batch_results = await crud.execute_item_batch(
                container, batch_operations_for_db, category_pk
            )
            # Extract created products from batch response format
            results = []
            for res_item in batch_results:
                if isinstance(res_item, dict):
                    if (
                        res_item.get("statusCode") in (200, 201)
                        and "resourceBody" in res_item
                    ):
                        try:
                            results.append(
                                ProductResponse.model_validate(res_item["resourceBody"])
                            )
                        except Exception:
                            continue
                    elif res_item.get("id"):
                        try:
                            results.append(ProductResponse.model_validate(res_item))
                        except Exception:
                            continue
            return results
        except Exception as e:
            await handle_batch_operation_error(
                e,
                "create",
                category_pk,
                product_list_for_category,
                lambda it, idx: {"sku": it.sku, "product_name": it.name},
            )

    # Execute concurrently using CRUD helper
    return await crud.execute_batch_by_category(
        products_by_category, process_category_creates
    )


async def update_products(
    container: ContainerProxy, batch_update: ProductBatchUpdate
) -> list[ProductResponse]:
    if not batch_update.items:
        return []

    updates_by_category: dict[str, list[Any]] = defaultdict(list)
    for update_item in batch_update.items:
        updates_by_category[normalize_category(update_item.category)].append(
            update_item
        )

    async def process_category_updates(
        category_pk: str, update_items_for_category: list[Any]
    ):
        batch_operations_for_db: list[tuple] = []

        for update_item in update_items_for_category:
            update_dict = update_item.changes.model_dump(exclude_unset=True)
            update_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
            update_dict = prepare_decimals_for_cosmos_db(update_dict)

            json_patch_operations = []
            for key, value in update_dict.items():
                if key not in ["id", "category", "_etag"]:
                    json_patch_operations.append(
                        {"op": "set", "path": f"/{key}", "value": value}
                    )

            if not json_patch_operations:
                continue

            batch_operations_for_db.append(
                (
                    "patch",
                    (update_item.id, json_patch_operations),
                    {"if_match_etag": update_item.etag},
                )
            )

        if not batch_operations_for_db:
            return []

        try:
            batch_results = await crud.execute_item_batch(
                container, batch_operations_for_db, category_pk
            )
            results = []
            for res_item in batch_results:
                if isinstance(res_item, dict):
                    if res_item.get("statusCode") == 200 and "resourceBody" in res_item:
                        try:
                            results.append(
                                ProductResponse.model_validate(res_item["resourceBody"])
                            )
                        except Exception:
                            continue
                    elif res_item.get("id"):
                        try:
                            results.append(ProductResponse.model_validate(res_item))
                        except Exception:
                            continue
            return results
        except Exception as e:
            await handle_batch_operation_error(
                e,
                "update",
                category_pk,
                update_items_for_category,
                lambda it, idx: {
                    "product_id": it.id,
                    **(
                        {"sku": it.changes.sku}
                        if getattr(it.changes, "sku", None)
                        else {}
                    ),
                    **(
                        {"product_name": it.changes.name}
                        if getattr(it.changes, "name", None)
                        else {}
                    ),
                },
            )

    return await crud.execute_batch_by_category(
        updates_by_category, process_category_updates
    )


async def delete_products(
    container: ContainerProxy, batch_delete: ProductBatchDelete
) -> list[str]:
    if not batch_delete.items:
        return []

    deletes_by_category: dict[str, list[str]] = defaultdict(list)
    for delete_item in batch_delete.items:
        deletes_by_category[normalize_category(delete_item.category)].append(
            delete_item.id
        )

    async def process_category_deletes(
        category_pk: str, product_ids_in_category: list[str]
    ):
        batch_operations_for_db: list[tuple] = []
        for product_id in product_ids_in_category:
            batch_operations_for_db.append(("delete", (product_id,), {}))

        if not batch_operations_for_db:
            return []

        try:
            await crud.execute_item_batch(
                container, batch_operations_for_db, category_pk
            )
            return product_ids_in_category
        except Exception as e:
            await handle_batch_operation_error(
                e,
                "delete",
                category_pk,
                product_ids_in_category,
                lambda it, idx: {"product_id": it},
            )

    return await crud.execute_batch_by_category(
        deletes_by_category, process_category_deletes
    )
