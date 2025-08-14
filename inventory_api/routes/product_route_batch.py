import logging

from azure.cosmos.aio import ContainerProxy
from fastapi import APIRouter, Depends, status

from inventory_api.db import ContainerType, get_container
from inventory_api.models.product import (
    ProductBatchCreate,
    ProductBatchDelete,
    ProductBatchUpdate,
    ProductResponse,
)
from inventory_api.services.product_batch_service import (
    create_products,
    delete_products,
    update_products,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products/batch", tags=["product-batch"])


async def get_products_container() -> ContainerProxy:
    return await get_container(ContainerType.PRODUCTS)


@router.post(
    "/", response_model=list[ProductResponse], status_code=status.HTTP_201_CREATED
)
async def add_products_batch(
    batch_create: ProductBatchCreate,
    container: ContainerProxy = Depends(get_products_container),
) -> list[ProductResponse]:
    return await create_products(container=container, batch_create=batch_create)


@router.patch("/", response_model=list[ProductResponse])
async def update_products_batch(
    batch_update: ProductBatchUpdate,
    container: ContainerProxy = Depends(get_products_container),
) -> list[ProductResponse]:
    return await update_products(container=container, batch_update=batch_update)


@router.delete("/", response_model=list[str])
async def delete_products_batch(
    batch_delete: ProductBatchDelete,
    container: ContainerProxy = Depends(get_products_container),
) -> list[str]:
    return await delete_products(container=container, batch_delete=batch_delete)
