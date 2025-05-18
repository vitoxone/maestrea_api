from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class LinkBase(BaseModel):
    url: str
    id_store: UUID

class LinkCreate(LinkBase):
    pass

class LinkRead(LinkBase):
    id: UUID
    name: Optional[str]
    active: bool
    deleted: bool

    class Config:
        orm_mode = True
