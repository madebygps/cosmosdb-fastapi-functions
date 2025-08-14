"""Base utilities for product CRUD operations."""

from decimal import Decimal
from typing import Any, Dict

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

    def convert_decimal(value: Any) -> Any:
        """Recursively convert Decimal values to float."""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, dict):
            return {k: convert_decimal(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [convert_decimal(item) for item in value]
        return value

    for key, value in data.items():
        data[key] = convert_decimal(value)

    return data
