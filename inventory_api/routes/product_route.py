import logging

from azure.cosmos.aio import ContainerProxy
from fastapi import APIRouter, Body, Depends, Header, Path, Query, status

from inventory_api.crud.product_crud import list_categories, list_products
from inventory_api.db import ContainerType, get_container
from inventory_api.models.product import (
    ProductCreate,
    ProductIdentifier,
    ProductList,
    ProductResponse,
    ProductUpdate,
    VersionedProductIdentifier,
)
from inventory_api.services.product_service import (
    create_product,
    delete_product,
    get_product_by_id,
    update_product,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


async def get_products_container() -> ContainerProxy:
    return await get_container(ContainerType.PRODUCTS)


@router.get("/categories", response_model=list[str])
async def get_categories(container: ContainerProxy = Depends(get_products_container)):
    return await list_categories(container=container)


@router.get("/", response_model=ProductList)
async def get_products_by_category(
    category: str = Query("electronics", title="The category to filter products by"),
    continuation_token: str | None = Query(None, title="Token for pagination"),
    limit: int = Query(50, title="Maximum number of items to return"),
    container: ContainerProxy = Depends(get_products_container),
):
    return await list_products(
        container=container,
        category=category,
        max_items=limit,
        continuation_token=continuation_token,
    )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def add_new_product(
    product: ProductCreate = Body(..., description="Product information to create"),
    container: ContainerProxy = Depends(get_products_container),
):
    return await create_product(container=container, product=product)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_product(
    id: str = Path(..., title="The ID of the product to delete"),
    category: str = Query(..., title="The category of the product (partition key)"),
    container: ContainerProxy = Depends(get_products_container),
):
    product_identifier = ProductIdentifier(id=id, category=category)
    await delete_product(container=container, product_identifier=product_identifier)


@router.patch("/{id}", response_model=ProductResponse)
async def update_existing_product(
    updated_product: ProductUpdate = Body(
        ...,
        description="Fields to update in the existing product",
    ),
    id: str = Path(..., title="The ID of the product to update"),
    category: str = Query(..., title="The category of the product (partition key)"),
    container: ContainerProxy = Depends(get_products_container),
    if_match_etag: str = Header(
        ...,
        alias="If-Match",
        description="ETag from the previous GET request for optimistic concurrency",
    ),
):
    identifier = VersionedProductIdentifier(
        id=id, category=category, _etag=if_match_etag
    )
    return await update_product(
        container=container, identifier=identifier, updates=updated_product
    )


@router.get("/{id}", response_model=ProductResponse)
async def get_product(
    id: str = Path(..., title="The ID of the product to retrieve"),
    category: str = Query(..., title="The category of the product (partition key)"),
    container: ContainerProxy = Depends(get_products_container),
):
    product = ProductIdentifier(id=id, category=category)
    return await get_product_by_id(container=container, identifier=product)
