from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# URL подключения к PostgreSQL (асинхронный)
DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/Test"

# Создание асинхронного движка
engine = create_async_engine(DATABASE_URL, echo=True)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Dependency для FastAPI
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]