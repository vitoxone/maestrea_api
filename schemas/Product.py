from pydantic import BaseModel, ConfigDict, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl

class ProductBase(BaseModel):
    name: str
    url: HttpUrl
    status: str = "incompleto"
    brand: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[int] = None
    stock: Optional[str] = None
    main_image: Optional[HttpUrl] = None
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    link_id: Optional[UUID] = None

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    id: UUID
    last_checked: Optional[datetime] = None
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    deleted: bool

    # 👇 solo esto (en v2)
    model_config = ConfigDict(from_attributes=True)

class ProductWithStore(ProductRead):
    webpage: Optional[str] = None
    store_name: Optional[str] = None    


class ProductsPage(BaseModel):
    products: list[ProductWithStore]
    total: int
    page: int
    pageSize: int = Field(alias="pageSize")
    totalPages: int