"""Core CRUD operations for products."""
import logging
import uuid
from datetime import datetime, timezone

from azure.cosmos.aio import ContainerProxy

from inventory_api.crud.cosmos_serialization import (
    normalize_category,
    prepare_decimals_for_cosmos_db,
)
from inventory_api.crud.product_queries import list_categories, list_products
from inventory_api.exceptions import handle_cosmos_error
from inventory_api.models.product import (
    ProductCreate,
    ProductIdentifier,
    ProductResponse,
    ProductStatus,
    ProductUpdate,
    VersionedProductIdentifier,
)

logger = logging.getLogger(__name__)

__all__ = [
    "create_product",
    "get_product_by_id",
    "update_product",
    "delete_product",
    "list_products",
    "list_categories",
]


async def create_product(
    container: ContainerProxy, product: ProductCreate
) -> ProductResponse:
    """
    Create a new product in the database.

    Args:
        container: Cosmos DB container client
        product: Product data to create

    Returns:
        Newly created product with system fields

    Raises:
        ProductAlreadyExistsError: If a product with same ID/SKU exists
        DatabaseError: If a database operation fails
    """
    data = product.model_dump()
    data["id"] = str(uuid.uuid4())
    data["status"] = ProductStatus.ACTIVE.value
    data["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Normalize category for consistent storage
    data["category"] = normalize_category(data["category"])

    # Convert Decimal to float for Cosmos DB
    data = prepare_decimals_for_cosmos_db(data)

    try:
        result = await container.create_item(body=data)
        return ProductResponse.model_validate(result)
    except Exception as e:
        logger.error(
            "Error during product creation",
            extra={
                "error_type": type(e).__name__,
                "product_id": data["id"],
                "category": data["category"],
                "sku": data.get("sku"),
                "product_name": data.get("name")
            },
            exc_info=True,
        )
        handle_cosmos_error(
            e,
            operation="create",
            category=data["category"],
            sku=data.get("sku"),
            product_name=data.get("name")
        )
        # This line will never be reached due to handle_cosmos_error raising an exception
        raise  # This satisfies the type checker


async def get_product_by_id(
    container: ContainerProxy, product: ProductIdentifier
) -> ProductResponse:
    """
    Retrieve a product by its ID and category.

    Args:
        container: Cosmos DB container client
        product: Product identifier with ID and category

    Returns:
        The retrieved product details

    Raises:
        ProductNotFoundError: If the product doesn't exist
        DatabaseError: If a database operation fails
    """
    normalized_category = normalize_category(product.category)

    try:
        item = await container.read_item(
            item=product.id, partition_key=normalized_category
        )
        return ProductResponse.model_validate(item)
    except Exception as e:
        logger.error(
            "Error retrieving product",
            extra={
                "product_id": product.id,
                "category": product.category,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        handle_cosmos_error(e, operation="get", product_id=product.id, category=product.category)
        # This line will never be reached due to handle_cosmos_error raising an exception
        raise  # This satisfies the type checker


async def update_product(
    container: ContainerProxy,
    identifier: VersionedProductIdentifier,
    updates: ProductUpdate
) -> ProductResponse:
    """
    Update an existing product.
    
    Args:
        container: Cosmos DB container client
        identifier: Product identifier with ID, category and ETag
        updates: Fields to update
    
    Returns:
        The updated product
    
    Raises:
        ProductNotFoundError: If the product doesn't exist
        ProductDuplicateSKUError: If updating to a SKU that already exists
        PreconditionFailedError: If the ETag doesn't match (concurrent update)
        DatabaseError: If a database operation fails
    """
    update_dict = updates.model_dump(exclude_unset=True)

    normalized_category = normalize_category(identifier.category)

    update_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Convert Decimal to float for Cosmos DB
    update_dict = prepare_decimals_for_cosmos_db(update_dict)

    # Create list of patch (set) operations
    patch_operations = []
    for key, value in update_dict.items():
        if key not in ["id", "category", "_etag"]: 
            patch_operations.append(
                {"op": "set", "path": f"/{key}", "value": value}
            )

    try:
        result = await container.patch_item(
            item=identifier.id,
            partition_key=normalized_category,
            patch_operations=patch_operations,
            headers={"if-match": identifier.etag},  # ETag for concurrency control
        )
        return ProductResponse.model_validate(result)
    except Exception as e:
        extra_context = {
            "error_type": type(e).__name__,
            "product_id": identifier.id,
            "category": normalized_category,
        }
        
        error_context = {
            "product_id": identifier.id,
            "category": identifier.category
        }
        
        if "sku" in update_dict:
            extra_context["sku"] = update_dict["sku"]
            error_context["sku"] = update_dict["sku"]
        
        if "name" in update_dict:
            extra_context["product_name"] = update_dict["name"]
            error_context["product_name"] = update_dict["name"]
            
        logger.error(
            "Error during product update",
            extra=extra_context,
            exc_info=True,
        )
        
        handle_cosmos_error(
            e, 
            operation="update", 
            **error_context 
        )
        # This line will never be reached due to handle_cosmos_error raising an exception
        raise  # This satisfies the type checker

async def delete_product(
    container: ContainerProxy,
    product_identifier: ProductIdentifier
) -> None:
    """
    Delete a product from the database.

    Args:
        container: Cosmos DB container client
        product_id: ID of the product to delete
        category: Category of the product (partition key)

    Raises:
        ProductNotFoundError: If the product doesn't exist
        DatabaseError: If a database operation fails
    """
    # Normalize category for consistent lookup
    normalized_category = normalize_category(product_identifier.category)

    try:
        await container.delete_item(
            item=product_identifier.id, partition_key=normalized_category
        )
    except Exception as e:
        logger.error(
            "Error during product deletion",
            extra={
                "error_type": type(e).__name__,
                "product_id": product_identifier.id,
                "category": normalized_category,
            },
            exc_info=True,
        )
        handle_cosmos_error(e, operation="delete", product_id=product_identifier.id, category=product_identifier.category)
