"""Batch operations for products."""
import asyncio
from collections import defaultdict
from azure.cosmos.aio import ContainerProxy
import uuid
from typing import Any, Dict, List, Tuple, TypeVar, Callable, Union
from datetime import datetime, timezone

from inventory_api.models.product import (
    ProductBatchCreate,
    ProductCreate,
    ProductResponse,
    ProductBatchUpdate,
    ProductBatchDelete,
    ProductStatus
)
import logging
from inventory_api.exceptions import handle_batch_operation_error

from inventory_api.crud.cosmos_serialization import normalize_category, prepare_decimals_for_cosmos_db

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


async def _execute_batch_by_category(
    items_by_category: Dict[str, List[T]],
    process_func: Callable[[str, List[T]], Any],
    result_extractor: Callable[[Any], List[R]] = None
) -> Union[List[R], List[Any]]:
    """
    Generic function to execute batch operations grouped by category with concurrent processing.
    
    Args:
        items_by_category: Dictionary mapping category to list of items
        process_func: Async function to process items for a single category
        result_extractor: Optional function to extract results from successful responses
        
    Returns:
        List of results from all successful operations
    """
    # Schedule tasks to run concurrently for each category
    tasks = [
        asyncio.create_task(process_func(category, items))
        for category, items in items_by_category.items()
    ]
    
    # Wait for all tasks to complete and gather results
    # Use return_exceptions=True to collect all results including exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check for exceptions and collect successful results
    all_results = []
    exceptions = []
    
    for result in results:
        if isinstance(result, Exception):
            exceptions.append(result)
        else:
            if result_extractor and result is not None:
                all_results.extend(result_extractor(result))
            elif result is not None:
                all_results.extend(result)
    
    # If there were any exceptions, raise the first one
    if exceptions:
        raise exceptions[0]
    
    return all_results


def _extract_product_responses(batch_results: List[dict], expected_status: int) -> List[ProductResponse]:
    """
    Extract ProductResponse objects from Cosmos DB batch results.
    
    Args:
        batch_results: Raw batch operation results from Cosmos DB
        expected_status: Expected HTTP status code for successful operations
        
    Returns:
        List of ProductResponse objects
    """
    products = []
    for result_item in batch_results:
        if isinstance(result_item, dict):
            # Extract the actual product data from resourceBody
            if "resourceBody" in result_item and result_item.get("statusCode") == expected_status:
                products.append(ProductResponse.model_validate(result_item["resourceBody"]))
            elif result_item.get("id"):
                # Fallback for different response format
                products.append(ProductResponse.model_validate(result_item))
            else:
                logger.warning(f"Unexpected item in batch result: {result_item}")
    return products



async def create_products(
    container: ContainerProxy,
    batch_create: ProductBatchCreate,
) -> List[ProductResponse]:
    """
    Create multiple products in a batch operation with concurrent processing across categories.
    
    Args:
        container: Cosmos DB container client
        batch_create: Batch create request containing items to create
        
    Returns:
        List of successfully created products
    """
    if not batch_create.items:
        return []
        
    # Batch processing requires grouping by partition key (category)
    products_by_category: Dict[str, List[ProductCreate]] = defaultdict(list)
    for product_model in batch_create.items:
        products_by_category[normalize_category(product_model.category)].append(product_model)

    async def process_category_creates(category_pk: str, product_list_for_category: List[ProductCreate]):
        if not product_list_for_category:
            return []
            
        batch_operations_for_db: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []

        # Add id, status, and last_updated to each product
        for product_to_create in product_list_for_category:
            data = product_to_create.model_dump()
            data["id"] = str(uuid.uuid4())
            data["status"] = ProductStatus.ACTIVE.value
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Normalize category for consistent storage
            data["category"] = normalize_category(data["category"])
            
            # Convert Decimal to float for Cosmos DB
            data = prepare_decimals_for_cosmos_db(data)
            
            # Add operation for product creation to the batch
            batch_operations_for_db.append(("create", (data,), {}))

        if not batch_operations_for_db:
            return []

        try:
            batch_results = await container.execute_item_batch(
                batch_operations=batch_operations_for_db, partition_key=category_pk
            )
            return _extract_product_responses(batch_results, expected_status=201)
        except Exception as e:
            def get_create_error_context(item: ProductCreate) -> Dict[str, Any]:
                return {
                    "sku": item.sku,
                    "product_name": item.name
                }
            
            await handle_batch_operation_error(
                e, "create", category_pk, product_list_for_category, get_create_error_context
            )

    return await _execute_batch_by_category(
        products_by_category,
        process_category_creates
    )


async def update_products(
    container: ContainerProxy,
    batch_update: ProductBatchUpdate,
) -> List[ProductResponse]:
    """
    Update multiple products in a batch operation with concurrent processing across categories.
    
    Args:
        container: Cosmos DB container client
        batch_update: Batch update request containing items to update
        
    Returns:
        List of successfully updated products
    """
    if not batch_update.items:
        return []

    updates_by_category: Dict[str, List] = defaultdict(list)
    for update_item in batch_update.items:
        updates_by_category[normalize_category(update_item.category)].append(update_item)
        
    async def process_category_updates(category_pk: str, update_items_for_category: List):
        if not update_items_for_category:
            return []
            
        batch_operations_for_db = []

        for update_item in update_items_for_category:
            update_dict = update_item.changes.model_dump(exclude_unset=True)
            
            update_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Convert Decimal to float for Cosmos DB
            update_dict = prepare_decimals_for_cosmos_db(update_dict)
            
            json_patch_operations = []
            for key, value in update_dict.items():
                if key not in ["id", "category", "_etag"]:
                    json_patch_operations.append(
                        {"op": "set", "path": f"/{key}", "value": value}
                    )

            if not json_patch_operations:
                logger.warning(
                    f"No valid patch operations for product ID '{update_item.id}' in category '{category_pk}'. Skipping."
                )
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
            batch_results = await container.execute_item_batch(
                batch_operations=batch_operations_for_db, partition_key=category_pk
            )
            return _extract_product_responses(batch_results, expected_status=200)
        except Exception as e:
            def get_update_error_context(item: Any) -> Dict[str, Any]:
                context = {"product_id": item.id}
                # Get SKU and name from the changes if they were being updated
                changes = item.changes.model_dump(exclude_unset=True)
                if "sku" in changes:
                    context["sku"] = changes["sku"]
                if "name" in changes:
                    context["product_name"] = changes["name"]
                return context
            
            await handle_batch_operation_error(
                e, "update", category_pk, update_items_for_category, get_update_error_context
            )

    return await _execute_batch_by_category(
        updates_by_category,
        process_category_updates
    )


async def delete_products(
    container: ContainerProxy,
    batch_delete: ProductBatchDelete,
) -> List[str]:
    """
    Delete multiple products in a batch operation with concurrent processing across categories.
    
    Args:
        container: Cosmos DB container client
        batch_delete: Batch delete request containing items to delete
        
    Returns:
        List of successfully deleted product IDs
    """
    if not batch_delete.items:
        return []

    deletes_by_category: Dict[str, List[str]] = defaultdict(list) 
    for delete_item in batch_delete.items:
        deletes_by_category[normalize_category(delete_item.category)].append(delete_item.id)

    async def process_category_deletes(category_pk: str, product_ids_in_category: List[str]):
        if not product_ids_in_category:
            return []
            
        batch_operations_for_db: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        
        for product_id in product_ids_in_category:
            batch_operations_for_db.append(("delete", (product_id,), {}))

        if not batch_operations_for_db:
            return []

        try:
            await container.execute_item_batch(
                batch_operations=batch_operations_for_db, partition_key=category_pk
            )
            # All deletes in this batch succeeded - return the IDs
            return product_ids_in_category
        except Exception as e:
            def get_delete_error_context(item_id: str) -> Dict[str, Any]:
                return {"product_id": item_id}
            
            await handle_batch_operation_error(
                e, "delete", category_pk, product_ids_in_category, get_delete_error_context
            )

    return await _execute_batch_by_category(
        deletes_by_category,
        process_category_deletes
    )