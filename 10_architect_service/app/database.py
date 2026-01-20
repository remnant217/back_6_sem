from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

'''
АГ
Мы будем работать с этой же БД Test? Или создадим новую БД для этого проекта?
Если будем продолжать работать с Test, то нужно очистить ее с предыдущих занятий.
Поэтому как будто стоит создать новую БД.
'''
# URL подключения к PostgreSQL (асинхронный)
DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/Test"

# Создание асинхронного движка
engine = create_async_engine(DATABASE_URL, echo=True)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]