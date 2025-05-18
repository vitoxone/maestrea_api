import uuid
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.Base import Base
from models.Category import Category 
from pydantic import ConfigDict


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    url = Column(String)
    status = Column(String)
    brand = Column(String)
    sku = Column(String)
    price = Column(Integer)
    stock = Column(String)
    main_image = Column(String)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    subcategory_id = Column(UUID(as_uuid=True), ForeignKey("subcategories.id"))
    link_id = Column(UUID(as_uuid=True), ForeignKey("links.id"))
    last_checked = Column(TIMESTAMP)
    created = Column(TIMESTAMP)
    modified = Column(TIMESTAMP)
    deleted = Column(Boolean, default=False)

    prices = relationship("Price", back_populates="product")
    link = relationship("Link", back_populates="products")
    category = relationship("Category", back_populates="products")
    subcategory = relationship("Subcategory", back_populates="products")