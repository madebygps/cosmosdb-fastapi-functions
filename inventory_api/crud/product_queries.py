"""Query operations for products (list, search, categories)."""
import logging
from builtins import anext

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
    max_items: int = DEFAULT_MAX_ITEMS
) -> ProductList:
    """
    Retrieve a paginated list of products by category.
    """
    
    # Normalize category for case-insensitive search
    normalized_category = normalize_category(category)
    
    query = "SELECT * FROM c WHERE c.category = @category"
    params = [{"name": "@category", "value": normalized_category}]

    # Create query options dictionary
    query_options = {"max_item_count": max_items}

    try:
        items = []
        next_continuation_token = None

        # Represents the entire potential result set of the query
        query_iterator = container.query_items(
            query=query, parameters=params, partition_key=category, **query_options
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

            # Get continuation token for next page from the page_iterator
            next_continuation_token = page_iterator.continuation_token
            

        except StopAsyncIteration:
            pass

        return ProductList(items=items, continuation_token=next_continuation_token)

    except Exception as e:
        logger.error(
            "Error during product listing",
            extra={
                "error_type": type(e).__name__,
                "category": category
            },
            exc_info=True
        )
        handle_cosmos_error(e, "list", category=category)


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
        
        # VALUE query returns the category directly, filter out empty values
        return [category async for category in query_iterator if category]
    except Exception as e:
        logger.error(
            "Error during category listing",
            extra={"error_type": type(e).__name__},
            exc_info=True
        )
        handle_cosmos_error(e, "list_categories")