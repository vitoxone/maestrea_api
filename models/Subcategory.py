import uuid
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.Base import Base
from models.Category import Category 


class Subcategory(Base):
    __tablename__ = "subcategories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    active = Column(Boolean, default=True)
    deleted = Column(Boolean, default=False)
    created = Column(TIMESTAMP)

    category = relationship("Category", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory") 



