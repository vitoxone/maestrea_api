from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class SubcategoryBase(BaseModel):
    name: str
    category_id: UUID

class SubcategoryCreate(SubcategoryBase):
    pass

class SubcategoryRead(SubcategoryBase):
    id: UUID
    active: Optional[bool] = True
    deleted: Optional[bool] = False
    created: Optional[datetime]

    class Config:
        orm_mode = True
