import uuid
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.Base import Base

class Category(Base):
    __tablename__ = "categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    deleted = Column(Boolean, default=False)
    created = Column(TIMESTAMP)

    subcategories = relationship("Subcategory", back_populates="category")  # ✅ corregido
    products = relationship("Product", back_populates="category") 
