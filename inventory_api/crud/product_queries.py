"""Query operations for products (list, search, categories)."""
from azure.cosmos.aio import ContainerProxy
from typing import Optional
from builtins import anext

from pydantic import ValidationError

import logging
from inventory_api.models.product import ProductResponse, ProductList
from inventory_api.exceptions import handle_cosmos_error
from .cosmos_serialization import normalize_category, DEFAULT_MAX_ITEMS

# Create a logger for this module
logger = logging.getLogger(__name__)


async def list_products(
    container: ContainerProxy,
    category: str,
    continuation_token: Optional[str] = None,
    max_items: int = DEFAULT_MAX_ITEMS
) -> ProductList:
    """
    Retrieve a paginated list of products by category.
    """
    
    # logger.info() removed for performance
    # logger.info(
    #     "Listing products", 
    #     extra={
    #         "category": category, 
    #         "max_items": max_items,
    #         "has_continuation_token": continuation_token is not None
    #     }
    # )
    
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

            # Get items in the page
            page_items = [item async for item in page]

            # Process items in the page
            for item in page_items:
                try:
                    product = ProductResponse.model_validate(item)
                    items.append(product)
                except ValidationError as e:
                    logger.debug(f"Pydantic validation errors: {e.errors()}")
                    continue

            # Get continuation token for next page from the page_iterator
            next_continuation_token = page_iterator.continuation_token
            
            # logger.info() removed for performance
            # logger.info(f"Retrieved {len(items)} products", extra={"count": len(items)})

        except StopAsyncIteration:
            # logger.info() removed for performance
            # logger.info("No results found or end of results reached")
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
    
    # logger.info() removed for performance
    # logger.info('Listing categories')
    
    # More efficient query using VALUE to return just the category strings
    query = "SELECT DISTINCT VALUE c.category FROM c WHERE IS_DEFINED(c.category) AND c.category != null"
    try:
        categories = []
        query_iterator = container.query_items(
            query=query
        )
        
        async for category in query_iterator:
            if category:  # VALUE query returns the category directly
                categories.append(category)
                
        # logger.info() removed for performance
        # count = len(categories)
        # logger.info(f"Retrieved {count} categories", extra={"count": count})
        return categories
    except Exception as e:
        logger.error(
            "Error during category listing",
            extra={"error_type": type(e).__name__},
            exc_info=True
        )
        handle_cosmos_error(e, "list_categories")