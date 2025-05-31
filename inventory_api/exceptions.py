import logging
from typing import Any, Callable

from azure.cosmos.exceptions import CosmosBatchOperationError, CosmosHttpResponseError
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class ApplicationError(Exception):
    """Base class for application-specific errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "An application error occurred"

class ProductNotFoundError(ApplicationError):
    """Raised when a product is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Product not found"

class ProductAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a product that already exists."""
    status_code = status.HTTP_409_CONFLICT
    detail = "Product already exists"

class DatabaseError(ApplicationError):
    """Raised for general database-related errors not specifically handled."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "A database error occurred"
    
    def __init__(self, message: str = "A database error occurred.", original_exception: Exception | None = None) -> None:
        super().__init__(message)
        self.original_exception = original_exception

class PreconditionFailedError(ApplicationError):
    """Raised when an optimistic concurrency check fails (ETag mismatch)."""
    status_code = status.HTTP_412_PRECONDITION_FAILED
    detail = "Precondition failed: resource was modified"

class ProductDuplicateSKUError(ApplicationError):
    """Raised when attempting to create or update a product with a SKU that already exists."""
    status_code = status.HTTP_409_CONFLICT
    detail = "A product with this SKU already exists"


def handle_cosmos_error(e: Exception, operation: str, **context: Any) -> None:
    """
    Convert Cosmos DB exceptions to application-specific exceptions.
    
    Args:
        e: The CosmosHttpResponseError or CosmosBatchOperationError exception
        operation: The operation being performed (e.g., "create", "update", "delete")
        **context: Additional context (e.g., product_id, category)
    
    Raises:
        Application-specific exception based on the error
    """
    
    # Handle batch operation errors
    if isinstance(e, CosmosBatchOperationError):
        # Extract status code from batch error - it's the overall batch status
        status_code = getattr(e, 'status_code', None)
        if status_code == 409:
            # Check if it's a duplicate SKU or ID error
            error_message = str(e).lower()
            if "unique index constraint" in error_message and "/sku" in error_message:
                sku = context.get("sku", "unknown")
                raise ProductDuplicateSKUError(
                    f"Product with SKU '{sku}' already exists"
                ) from e
            else:
                # Handle ID conflicts - prefer showing SKU if available
                sku = context.get("sku")
                if sku:
                    raise ProductAlreadyExistsError(
                        f"Product with SKU '{sku}' already exists"
                    ) from e
                else:
                    product_name = context.get("product_name", "unknown")
                    raise ProductAlreadyExistsError(
                        f"Product '{product_name}' already exists"
                    ) from e
        else:
            # Other batch errors
            raise DatabaseError(
                f"Batch operation error during {operation}: {str(e)}",
                original_exception=e
            ) from e
    
    if not isinstance(e, CosmosHttpResponseError):
        raise DatabaseError(
            f"An unexpected error occurred during {operation} operation.",
            original_exception=e
        ) from e
    
    if e.status_code == 404:
        if operation in {"update", "delete", "get"}:
            product_id = context.get("product_id", "unknown")
            category = context.get("category", "unknown")
            raise ProductNotFoundError(
                f"Product with ID '{product_id}' and category '{category}' not found"
            ) from e
    elif e.status_code == 409:
        if operation in {"create", "update"}:
            error_message = str(e).lower()
            if "unique index constraint" in error_message and "/sku" in error_message:
                sku = context.get("sku", "unknown")
                raise ProductDuplicateSKUError(
                    f"Product with SKU '{sku}' already exists"
                ) from e
            else:
                # Handle other 409 conflicts - prefer showing SKU if available
                sku = context.get("sku")
                if sku:
                    raise ProductAlreadyExistsError(
                        f"Product with SKU '{sku}' already exists"
                    ) from e
                else:
                    product_name = context.get("product_name", "unknown")
                    raise ProductAlreadyExistsError(
                        f"Product '{product_name}' already exists"
                    ) from e
    elif e.status_code == 412:
        if operation == "update":
            product_id = context.get("product_id", "unknown")
            raise PreconditionFailedError(
                f"Product with ID '{product_id}' has been modified since last retrieved (ETag mismatch)."
            ) from e
    
    # Default case
    raise DatabaseError(
        f"Cosmos DB error during {operation}: Status Code {e.status_code}, Message: {e.message}",
        original_exception=e
    ) from e


async def handle_batch_operation_error(
    e: Exception,
    operation: str,
    category_pk: str,
    items: list[Any],
    get_error_context: Callable[[Any, int], dict[str, Any]]
) -> None:
    """
    Handle batch operation errors with consistent logging and error context extraction.
    
    Args:
        e: The exception that occurred
        operation: The operation being performed (create, update, delete)
        category_pk: The partition key (category)
        items: The list of items being processed
        get_error_context: Function to extract error context from a failed item
    """
    logger = logging.getLogger("inventory_api.exceptions")
    
    if isinstance(e, CosmosBatchOperationError):
        logger.error(
            f"Cosmos DB Batch {operation.title()} Error for category '{category_pk}': "
            f"First failed op index: {e.error_index}. Msg: {str(e)}",
            exc_info=True,
        )
        
        error_context = {"category": category_pk}
        
        # Extract details of the specific item that caused the batch to fail
        if e.error_index is not None and e.error_index < len(items):
            failed_item_context = get_error_context(items[e.error_index], e.error_index)
            error_context.update(failed_item_context)
        
        # Log the specific failures for debugging
        for i, op_response in enumerate(e.operation_responses):
            if i < len(items) and op_response.get("statusCode", 200) >= 400:
                item_info = get_error_context(items[i], i)
                item_desc = item_info.get("sku") or item_info.get("product_id", "unknown")
                logger.error(
                    f"  Failed {operation} op in batch for item '{item_desc}': {op_response}"
                )
        
        # Re-raise with proper context
        handle_cosmos_error(e, operation=operation, **error_context)
    else:
        logger.error(
            f"Error during batch {operation} for category '{category_pk}'",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.
    This centralizes all error handling in one place.
    """
    
    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        """Handle application-specific errors."""
        # Get the logger for the current module if possible
        logger = None
        try:
            if request.scope.get("route") and request.scope.get("route").endpoint.__module__:
                logger = logging.getLogger(request.scope.get("route").endpoint.__module__)
        except (AttributeError, KeyError):
            # Fallback to a default logger if we can't get the module
            logger = logging.getLogger("api.error_handler")
        
        # Log at appropriate level based on status code
        if logger:
            log_level = "warning" if exc.status_code < 500 else "error"
            extra = {"error_type": type(exc).__name__}
            
            # Add original exception info if available
            original_exc = getattr(exc, "original_exception", None)
            if hasattr(logger, log_level):
                if original_exc:
                    getattr(logger, log_level)(
                        str(exc),
                        extra=extra,
                        exc_info=original_exc
                    )
                else:
                    getattr(logger, log_level)(str(exc), extra=extra)
        
        # Return appropriate HTTP response
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc)}
        )
    
    # Special handler for CosmosDB errors that weren't caught
    @app.exception_handler(CosmosHttpResponseError)
    async def cosmos_exception_handler(request: Request, exc: CosmosHttpResponseError) -> JSONResponse:
        """Handle any uncaught Cosmos DB errors."""
        # Convert to application error first
        db_error = DatabaseError(f"Database error: {str(exc)}", original_exception=exc)
        
        # Then handle using the application error handler
        return await application_error_handler(request, db_error)
    
    # Special handler for CosmosDB batch errors that weren't caught
    @app.exception_handler(CosmosBatchOperationError)
    async def cosmos_batch_exception_handler(request: Request, exc: CosmosBatchOperationError) -> JSONResponse:
        """Handle any uncaught Cosmos DB batch errors."""
        # Convert to application error first
        db_error = DatabaseError(f"Batch operation error: {str(exc)}", original_exception=exc)
        
        # Then handle using the application error handler
        return await application_error_handler(request, db_error)
    
    @app.exception_handler(Exception)
    async def fallback_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle any unhandled exceptions as a fallback."""
        # Get the logger
        logger = None
        try:
            if request.scope.get("route") and request.scope.get("route").endpoint.__module__:
                logger = logging.getLogger(request.scope.get("route").endpoint.__module__)
        except (AttributeError, KeyError):
            logger = logging.getLogger("api.error_handler")
            
        # Always log at error level for unexpected exceptions
        if logger:
            logger.error(
                f"Unhandled exception: {str(exc)}",
                extra={"error_type": type(exc).__name__},
                exc_info=exc
            )
        
        # Generic 500 error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred"}
        )