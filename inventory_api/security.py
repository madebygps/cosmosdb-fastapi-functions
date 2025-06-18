import logging
from typing import Any

from fastapi import HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, APIKeyQuery

logger = logging.getLogger(__name__)

API_KEY_NAME = "x-functions-key"
api_key_header_scheme = APIKeyHeader(
    name=API_KEY_NAME,
    auto_error=False,
    scheme_name="ApiKeyAuthHeader",
    description="API Key (x-functions-key) in header",
)
api_key_query_scheme = APIKeyQuery(
    name="code",
    auto_error=False,
    scheme_name="ApiKeyAuthQuery",
    description="API Key (code) in query string",
)


def _get_azure_function_key(request: Request) -> str | None:
    """
    Safely retrieves the Azure Function key from the request context.
    Uses try-except for cleaner attribute access.
    """
    try:
        function_context = getattr(request, "function_context", None)
        if function_context:
            function_directory = getattr(function_context, "function_directory", None)
            if function_directory:
                return function_directory.get_function_key()
    except (AttributeError, TypeError):
        pass
    return None


async def get_api_key(
    req: Request,
    api_key_from_header: str = Security(api_key_header_scheme),
    api_key_from_query: str = Security(api_key_query_scheme),
) -> str:
    """Validate API key from header or query against Azure Function key if available."""
    client_api_key = api_key_from_header or api_key_from_query
    azure_expected_key = _get_azure_function_key(req)

    if azure_expected_key:
        if not client_api_key or client_api_key != azure_expected_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key.",
            )
    elif not client_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required.",
        )
    return client_api_key


async def check_api_key_for_docs(request: Request, call_next) -> JSONResponse | Any:
    """
    Middleware to protect documentation endpoints if running in Azure
    and an Azure Function key is configured.
    """
    openapi_url = "/api/openapi.json"
    docs_url = "/docs"

    path = request.url.path
    is_doc_path = path in [docs_url, openapi_url]

    if is_doc_path:
        azure_expected_key = _get_azure_function_key(request)
        if azure_expected_key:
            client_api_key = request.headers.get(
                API_KEY_NAME
            ) or request.query_params.get("code")

            if not client_api_key or client_api_key != azure_expected_key:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Access to documentation requires a valid API key."
                    },
                )
    response = await call_next(request)
    return response
