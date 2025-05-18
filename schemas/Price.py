from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class PriceBase(BaseModel):
    product_id: UUID
    price: int
    date: datetime

class PriceCreate(PriceBase):
    pass

class PriceRead(PriceBase):
    id: UUID

    class Config:
        orm_mode = True
