import logging
from typing import Any

import azure.functions as func
from fastapi import FastAPI, HTTPException, Request, Security, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader, APIKeyQuery

from inventory_api.exceptions import register_exception_handlers, DatabaseError
from inventory_api.routes.product_route import router as product_router
from inventory_api.routes.product_route_batch import router as product_batch_router

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


app = FastAPI(
    title="Inventory API",
    version="1.0.0",
    openapi_url="/api/openapi.json",   
    docs_url=None,  
    redoc_url=None, 
    openapi_components={
        "securitySchemes": {
            api_key_header_scheme.scheme_name: api_key_header_scheme.model.model_dump(
                exclude_none=True
            ),
            api_key_query_scheme.scheme_name: api_key_query_scheme.model.model_dump(
                exclude_none=True
            ),
        }
    },
    dependencies=[Security(get_api_key)],
)

register_exception_handlers(app)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    cdn_swagger_js_url = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.js"
    cdn_swagger_css_url = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.css"
    cdn_favicon_url = "https://fastapi.tiangolo.com/img/favicon.png"

    return get_swagger_ui_html(
        openapi_url="",
        title=app.title + " - Swagger UI",
        swagger_ui_parameters={"spec": app.openapi()},
        swagger_js_url=cdn_swagger_js_url,
        swagger_css_url=cdn_swagger_css_url,
        swagger_favicon_url=cdn_favicon_url,
    )


def _get_azure_function_key(request: Request) -> str | None:
    """
    Safely retrieves the Azure Function key from the request context.
    Uses try-except for cleaner attribute access.
    """
    try:
        function_context = getattr(request, 'function_context', None)
        if function_context:
            function_directory = getattr(function_context, 'function_directory', None)
            if function_directory:
                return function_directory.get_function_key()
    except (AttributeError, TypeError):
        pass
    return None


@app.middleware("http")
async def check_api_key_for_docs(request: Request, call_next) -> JSONResponse | Any:
    """
    Middleware to protect documentation endpoints if running in Azure
    and an Azure Function key is configured.
    """
    path = request.url.path
    is_doc_path = path in [app.docs_url, app.redoc_url, app.openapi_url]

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

app.include_router(product_router)
app.include_router(product_batch_router)

# Debug test endpoint
@app.get("/debug-test")
async def debug_test():
    """Test endpoint to trigger exception for debugging."""
    logger.info("Debug test endpoint called")
    # This will trigger the DatabaseError.__init__ method where your breakpoint is set
    raise DatabaseError("This is a test database error for debugging")

function_app = func.FunctionApp()


@function_app.route(route="{*route}", auth_level=func.AuthLevel.FUNCTION)
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions entry‑point routed through FastAPI."""
    return await func.AsgiMiddleware(app).handle_async(req)