"""Core CRUD operations for products."""

import logging

from azure.cosmos.aio import ContainerProxy

from inventory_api.crud.product_queries import list_categories, list_products
from inventory_api.exceptions import handle_cosmos_error
from inventory_api.models.product import ProductIdentifier, VersionedProductIdentifier

logger = logging.getLogger(__name__)

__all__ = [
    "create_product",
    "get_product_by_id",
    "update_product",
    "delete_product",
    "list_products",
    "list_categories",
]


async def create_product(container: ContainerProxy, item: dict) -> dict:
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
    # Expect `item` to be a fully prepared dict ready for Cosmos DB.
    try:
        result = await container.create_item(body=item)
        # Return raw DB result; service layer will convert/validate into models
        return result
    except Exception as e:
        logger.error(
            "Error during product creation",
            extra={
                "error_type": type(e).__name__,
                "product_id": item.get("id") if isinstance(item, dict) else None,
                "category": item.get("category") if isinstance(item, dict) else None,
                "sku": item.get("sku") if isinstance(item, dict) else None,
                "product_name": item.get("name") if isinstance(item, dict) else None,
            },
            exc_info=True,
        )
        handle_cosmos_error(
            e,
            operation="create",
            category=(item.get("category") if isinstance(item, dict) else None),
            sku=(item.get("sku") if isinstance(item, dict) else None),
            product_name=(item.get("name") if isinstance(item, dict) else None),
        )
        # This line will never be reached due to handle_cosmos_error raising an exception
        raise  # This satisfies the type checker


async def get_product_by_id(
    container: ContainerProxy, product: ProductIdentifier
) -> dict:
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
    try:
        item = await container.read_item(
            item=product.id, partition_key=product.category
        )
        return item
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
        handle_cosmos_error(
            e, operation="get", product_id=product.id, category=product.category
        )
        # This line will never be reached due to handle_cosmos_error raising an exception
        raise  # This satisfies the type checker


async def update_product(
    container: ContainerProxy,
    identifier: VersionedProductIdentifier,
    patch_operations: list[dict],
    if_match: str | None = None,
) -> dict:
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
    try:
        headers = {"if-match": if_match} if if_match else None
        result = await container.patch_item(
            item=identifier.id,
            partition_key=identifier.category,
            patch_operations=patch_operations,
            headers=headers,
        )
        return result
    except Exception as e:
        extra_context = {
            "error_type": type(e).__name__,
            "product_id": identifier.id,
            "category": identifier.category,
        }
        error_context = {"product_id": identifier.id, "category": identifier.category}

        # Try to extract sku/name from patch_operations if present
        try:
            for op in patch_operations or []:
                if isinstance(op, dict) and op.get("op") == "set":
                    path = op.get("path", "")
                    val = op.get("value")
                    if path == "/sku" and val is not None:
                        extra_context["sku"] = str(val)
                        error_context["sku"] = str(val)
                    if path == "/name" and val is not None:
                        extra_context["product_name"] = str(val)
                        error_context["product_name"] = str(val)
        except Exception:
            # Safely ignore any extraction errors
            pass
        logger.error(
            "Error during product update",
            extra=extra_context,
            exc_info=True,
        )

        handle_cosmos_error(e, operation="update", **error_context)
        # This line will never be reached due to handle_cosmos_error raising an exception
        raise  # This satisfies the type checker


async def delete_product(
    container: ContainerProxy, product_identifier: ProductIdentifier
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
    try:
        await container.delete_item(
            item=product_identifier.id, partition_key=product_identifier.category
        )
    except Exception as e:
        logger.error(
            "Error during product deletion",
            extra={
                "error_type": type(e).__name__,
                "product_id": product_identifier.id,
                "category": product_identifier.category,
            },
            exc_info=True,
        )
        handle_cosmos_error(
            e,
            operation="delete",
            product_id=product_identifier.id,
            category=product_identifier.category,
        )
