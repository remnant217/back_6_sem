'''
АГ
Если будем использовать для аннотации AsyncGenerator,
то лучше отдельно на занятии пояснить что это такое, зачем надо.
И потом в функции get_session() также стоит пояснить возвращаемый
тип AsyncGenerator[AsyncSession, None] - почему так строится.

Добавил строчку SessionDep = Annotated[AsyncSession, Depends(get_session)],
логичнее, чтобы она была тут. Конечно, это слегка нарушает архитектуру,
и лучше вообще добавить отдельный файл для хранения зависимостей deps.py,
но пока зависимость у нас одна - можем хранить и тут.
'''
# from typing import AsyncGenerator, Annotated

# from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# from sqlmodel.ext.asyncio.session import AsyncSession
# from fastapi import Depends

# DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/books_db"

# engine = create_async_engine(DATABASE_URL, echo=False)
# SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# async def get_session() -> AsyncGenerator[AsyncSession, None]:
#     async with SessionLocal() as session:
#         yield session

# SessionDep = Annotated[AsyncSession, Depends(get_session)]

from typing import AsyncGenerator, Annotated

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app.core.settings import settings

engine = create_async_engine(settings.database_url, echo=settings.DB_ECHO)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]