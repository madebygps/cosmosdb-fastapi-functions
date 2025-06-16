---
applyTo: "**.py"
---

# FastAPI + Python Best Practices

**Type Safety**: Use complete type annotations. All functions async with proper `async def` and `await`.

**FastAPI Patterns**: Use `APIRouter`, `Depends()` for dependency injection, explicit `status_code` and `response_model` on routes.

**Error Handling**: Custom exceptions from [inventory_api/exceptions.py](inventory_api/exceptions.py). Log with structured context: `logger.error("msg", extra=context, exc_info=True)`.

**Models**: Pydantic models with `Field()` validation. Separate Create/Update/Response models.

**Code Organization**: Follow layered structure - routes/ (HTTP), crud/ (business logic), models/ (validation).

**Patterns**: Reference [inventory_api/routes/product_route.py](inventory_api/routes/product_route.py) for route structure, [inventory_api/models/product.py](inventory_api/models/product.py) for validation.