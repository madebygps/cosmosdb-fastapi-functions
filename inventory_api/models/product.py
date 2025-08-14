from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class ProductStatus(str, Enum):
    """
    Status options for products in the inventory system.
    ACTIVE: Product is available for sale
    INACTIVE: Product is not available (discontinued, seasonal, etc.)
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class Product(BaseModel):
    """Fields that are intrinsic to a product"""

    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[Optional[str], Field(None, max_length=1000)]
    category: Annotated[str, Field(min_length=1, max_length=100)]
    price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    sku: Annotated[str, Field(min_length=1, max_length=50, pattern=r"^[A-Z0-9-]+$")]
    quantity: Annotated[int, Field(ge=0)] = 0
    status: ProductStatus = ProductStatus.ACTIVE

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_serializer("price")
    def _serialize_price(self, v: Decimal, _info):
        # Serialize Decimal to float for JSON output (two decimal places are enforced by validation)
        return float(v)


class ProductCreate(Product):
    """
    Fields a client needs to provide to create a product.
    Inherits all fields from Product base class but a separate class for future extensibility.
    """

    pass


class ProductUpdate(BaseModel):
    """
    Fields a client can provide to update a product.
    Only contains fields that clients are allowed to modify.
    """

    # Update fields (all optional)
    name: Annotated[Optional[str], Field(None, min_length=1, max_length=255)]
    description: Annotated[Optional[str], Field(None, max_length=1000)]
    price: Annotated[Optional[Decimal], Field(None, gt=0, decimal_places=2)]
    quantity: Annotated[Optional[int], Field(None, ge=0)]
    status: Optional[ProductStatus] = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if not any(
            getattr(self, field) is not None for field in self.__class__.model_fields
        ):
            raise ValueError("At least one update field must be provided")
        return self


class ProductIdentifier(BaseModel):
    """Fields required to uniquely identify a product in the database"""

    id: str
    category: str  # Used for partitioning in CosmosDB

    model_config = ConfigDict(extra="forbid")


class VersionedProductIdentifier(ProductIdentifier):
    """Product identifier with optimistic concurrency control"""

    etag: str = Field(alias="_etag")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProductResponse(Product):
    """
    All product fields plus system-generated fields.
    This is what clients receive when requesting product details.
    Inherits all core fields from Product base class.
    """

    id: str
    etag: str = Field(alias="_etag")  # Cosmos DB concurrency control token
    last_updated: datetime

    # Cosmos DB system fields (always present when reading from DB)
    _rid: str
    _self: str
    _attachments: str
    _ts: int

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_serializer("last_updated")
    def _serialize_last_updated(self, v: datetime, _info):
        # Convert datetime to ISO-8601 string for JSON output
        return v.isoformat()

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """
        Custom validation to handle datetime parsing and field mapping.
        """
        # If last_updated is not provided, use _ts to set it
        if "last_updated" not in obj and "_ts" in obj:
            obj["last_updated"] = datetime.fromtimestamp(obj["_ts"])
        return super().model_validate(obj, *args, **kwargs)


class BatchOperation(BaseModel):
    """Base class for all batch operations"""

    model_config = ConfigDict(extra="forbid")


class ProductBatchCreate(BatchOperation):
    """
    Request model for creating multiple products in a single operation.
    """

    items: Annotated[List[ProductCreate], Field(min_length=1, max_length=100)]


class ProductBatchUpdateItem(VersionedProductIdentifier):
    """
    Represents a single product to update in a batch request.
    Inherits identification fields and adds update changes.
    """

    changes: ProductUpdate

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProductBatchUpdate(BatchOperation):
    """
    Request model for updating multiple products in a single operation.
    """

    items: Annotated[List[ProductBatchUpdateItem], Field(min_length=1, max_length=100)]


class ProductBatchDeleteItem(ProductIdentifier):
    """
    Represents a single product to delete in a batch request.
    Only requires identification fields, no etag needed for deletion.
    """

    pass


class ProductBatchDelete(BatchOperation):
    """
    Request model for deleting multiple products in a single operation.
    """

    items: Annotated[List[ProductBatchDeleteItem], Field(min_length=1, max_length=100)]


class ProductList(BaseModel):
    """
    Response model for paginated product lists.
    Includes both the list of products and a continuation token for pagination.
    """

    items: list[ProductResponse]
    continuation_token: Optional[str] = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)
