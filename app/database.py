from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,   # 👈 versión pensada para async
)
from sqlalchemy.orm import declarative_base
from app.config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,               # "postgresql+asyncpg://user:pass@host/db"
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Fábrica principal
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session