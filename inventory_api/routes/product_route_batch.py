from typing import List
from fastapi import APIRouter, status, Depends
from inventory_api.models.product import (
    ProductResponse, 
    ProductBatchCreate,
    ProductBatchUpdate,
    ProductBatchDelete
)
from inventory_api.crud.product_crud_batch import (
    create_products,
    update_products,
    delete_products
)
import logging
from inventory_api.db import get_container, ContainerType
from azure.cosmos.aio import ContainerProxy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products/batch", tags=["product-batch"])


async def get_products_container() -> ContainerProxy:
    return await get_container(ContainerType.PRODUCTS)


@router.post("/", response_model=List[ProductResponse], status_code=status.HTTP_201_CREATED)
async def add_products_batch(
    batch_create: ProductBatchCreate,
    container: ContainerProxy = Depends(get_products_container),
):
    return await create_products(container=container, batch_create=batch_create)


@router.patch("/", response_model=List[ProductResponse])
async def update_products_batch(
    batch_update: ProductBatchUpdate,
    container: ContainerProxy = Depends(get_products_container),
):
    return await update_products(container=container, batch_update=batch_update)


@router.delete("/", response_model=List[str])
async def delete_products_batch(
    batch_delete: ProductBatchDelete,
    container: ContainerProxy = Depends(get_products_container),
):
    return await delete_products(container=container, batch_delete=batch_delete)