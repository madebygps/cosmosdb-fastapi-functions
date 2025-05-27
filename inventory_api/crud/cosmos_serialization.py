"""Base utilities for product CRUD operations."""
from typing import Any, Dict
from decimal import Decimal

# Constants for Cosmos DB operations
DEFAULT_MAX_ITEMS = 50
MAX_BATCH_SIZE = 100  # Cosmos DB batch operation limit


def normalize_category(category: str) -> str:
    """
    Normalize category for case-insensitive operations.
    
    Args:
        category: The original category string
        
    Returns:
        Normalized category string (lowercase)
    """
    if not category or not isinstance(category, str):
        raise ValueError("Category must be a non-empty string")
    return category.lower().strip()


def prepare_decimals_for_cosmos_db(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Decimal values to float for Cosmos DB storage (in-place).
    
    Args:
        data: Dictionary containing data to serialize
        
    Returns:
        The same dictionary with Decimal values converted to float
    """
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = float(value)
        elif isinstance(value, dict):
            prepare_decimals_for_cosmos_db(value)
        elif isinstance(value, list):
            data[key] = [
                prepare_decimals_for_cosmos_db(item) if isinstance(item, dict) else 
                float(item) if isinstance(item, Decimal) else item 
                for item in value
            ]
    return data