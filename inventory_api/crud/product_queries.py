import logging
from builtins import anext
from typing import Any, Dict, List

from azure.cosmos.aio import ContainerProxy
from pydantic import ValidationError

from inventory_api.exceptions import handle_cosmos_error
from inventory_api.models.product import ProductList, ProductResponse

from .cosmos_serialization import DEFAULT_MAX_ITEMS, normalize_category

logger = logging.getLogger(__name__)


async def list_products(
    container: ContainerProxy,
    category: str,
    continuation_token: str | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> ProductList:
    """
    Retrieve a paginated list of products by category.
    """

    # Normalize category for case-insensitive search
    normalized_category = normalize_category(category)

    query = "SELECT * FROM c WHERE c.category = @category"
    params: List[Dict[str, Any]] = [{"name": "@category", "value": normalized_category}]

    try:
        items = []
        next_continuation_token = None

        # Represents the entire potential result set of the query
        query_iterator = container.query_items(
            query=query,
            parameters=params,
            partition_key=category,
            max_item_count=max_items,
        )

        # Mechanism to get page (subset) of total result set at a time
        page_iterator = query_iterator.by_page(continuation_token)

        try:
            # Get page of items
            page = await anext(page_iterator)

            # Process items directly from the async generator
            async for item in page:
                try:
                    items.append(ProductResponse.model_validate(item))
                except ValidationError as e:
                    logger.debug(f"Pydantic validation errors: {e.errors()}")
                    continue

            # Get continuation token for next page
            try:
                # Check if there are more pages
                await anext(page_iterator)
                # If we get here, there are more pages, so we need the continuation token
                # Since we can't get the token directly, we'll use the response token
                next_continuation_token = "has_more_pages"
            except StopAsyncIteration:
                # No more pages
                next_continuation_token = None

        except StopAsyncIteration:
            pass

        return ProductList(items=items, continuation_token=next_continuation_token)

    except Exception as e:
        logger.error(
            "Error during product listing",
            extra={"error_type": type(e).__name__, "category": category},
            exc_info=True,
        )
        handle_cosmos_error(e, "list", category=category)
        return ProductList(
            items=[], continuation_token=None
        )  # This line will never be reached due to handle_cosmos_error raising an exception


async def list_categories(container: ContainerProxy) -> list[str]:
    """
    Retrieve all unique product categories.

    Returns:
        List of unique category names

    Raises:
        DatabaseError: If a database operation fails
    """

    # More efficient query using VALUE to return just the category strings
    query = (
        "SELECT DISTINCT VALUE c.category FROM c "
        "WHERE IS_DEFINED(c.category) AND c.category != null"
    )
    try:
        query_iterator = container.query_items(query=query)

        # VALUE query returns the category strings directly
        categories = []
        async for category in query_iterator:
            if category and isinstance(category, str):
                categories.append(category)

        return categories
    except Exception as e:
        logger.error(
            "Error during category listing",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        handle_cosmos_error(e, "list_categories")
        return (
            []
        )  # This line will never be reached due to handle_cosmos_error raising an exception
