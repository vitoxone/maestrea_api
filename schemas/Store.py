from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
from datetime import datetime

class StoreBase(BaseModel):
    name: str
    webpage: Optional[str]
    selectors: Optional[Any]
    paginator: Optional[Any]

class StoreCreate(StoreBase):
    pass

class StoreRead(StoreBase):
    id: UUID
    active: bool
    last_ejecution: Optional[datetime]
    created: Optional[datetime]
    modified: Optional[datetime]
    deleted: bool

    class Config:
        orm_mode = True
