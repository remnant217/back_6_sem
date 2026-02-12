# from typing import Annotated

# from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# from sqlmodel.ext.asyncio.session import AsyncSession
# from fastapi import Depends

# DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/books_db"

# engine = create_async_engine(DATABASE_URL, echo=False)
# AsyncSessionLocal = async_sessionmaker(bind=engine,
#                                        expire_on_commit = False)
#
# async def get_session():
#     async with AsyncSessionLocal() as session:
#         yield session

# SessionDep = Annotated[AsyncSession, Depends(get_session)]

from typing import Annotated

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app.core.settings import settings

engine = create_async_engine(settings.database_url, echo=settings.DB_ECHO)

AsyncSessionLocal = async_sessionmaker(bind=engine,
                                       expire_on_commit = False)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

