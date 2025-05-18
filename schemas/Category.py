from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: UUID
    active: Optional[bool] = True
    deleted: Optional[bool] = False
    created: Optional[datetime]

    class Config:
        orm_mode = True

