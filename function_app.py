import logging

import azure.functions as func
from fastapi import FastAPI, Security
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from inventory_api.exceptions import register_exception_handlers
from inventory_api.routes.product_route import router as product_router
from inventory_api.routes.product_route_batch import router as product_batch_router
from inventory_api.security import check_api_key_for_docs, get_api_key

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Inventory API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
    dependencies=[Security(get_api_key)],
)

register_exception_handlers(app)
app.middleware("http")(check_api_key_for_docs)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="",
        title=app.title + " - Swagger UI",
        swagger_ui_parameters={"spec": app.openapi()},
    )


app.include_router(product_router)
app.include_router(product_batch_router)


function_app = func.FunctionApp()


@function_app.route(route="{*route}", auth_level=func.AuthLevel.FUNCTION)
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions entry‑point routed through FastAPI."""
    return await func.AsgiMiddleware(app).handle_async(req)
