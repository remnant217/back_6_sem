from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# URL подключения к PostgreSQL (асинхронный)
DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/Test"

# Создание асинхронного движка
engine = create_async_engine(DATABASE_URL, echo=True)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Dependency для FastAPI
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]