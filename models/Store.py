import uuid
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID,JSONB
from sqlalchemy.orm import relationship
from models.Base import Base

class Store(Base):
    __tablename__ = "stores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    webpage = Column(String)
    selectors = Column(JSONB)
    paginator = Column(JSONB)
    active = Column(Boolean, default=True)
    last_ejecution = Column(TIMESTAMP)
    created = Column(TIMESTAMP)
    modified = Column(TIMESTAMP)
    deleted = Column(Boolean, default=False)

    links = relationship("Link", back_populates="store")
