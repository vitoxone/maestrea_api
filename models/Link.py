import uuid
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.Base import Base

class Link(Base):
    __tablename__ = "links"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    url = Column(String, nullable=False)
    id_store = Column(UUID(as_uuid=True), ForeignKey("stores.id"))
    active = Column(Boolean, default=True)
    deleted = Column(Boolean, default=False)

    products = relationship("Product", back_populates="link")
    store = relationship("Store", back_populates="links") 