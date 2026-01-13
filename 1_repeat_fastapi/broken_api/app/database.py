from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from app.models import Base, Item

# асинхронный URL БД для основного приложения
ASYNC_DATABASE_URL = 'sqlite+aiosqlite:///./items.db'

# асинхронный движок 
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
)

# фабрика асинхронных сессий
AsyncSessionLocal = async_sessionmaker(bind=async_engine,expire_on_commit=False)

# функция для создания таблицы в БД, если ее еще нет
def init_db():
    # используем отдельный синхронный движок только для create_all()
    sync_engine = create_engine('sqlite:///./items.db')
    Base.metadata.create_all(bind=sync_engine)

# асинхронная зависимость для получения сессии БД
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# вернуть список всех товаров с возможностью фильтрации
async def list_items(db: AsyncSession, q: str | None = None) -> list[Item]:
    statement = select(Item)
    result = await db.execute(statement)
    items = result.scalars().all()
    return items

# вернуть один товар по ID
async def get_item(db: AsyncSession, item_id: int) -> Item | None:
    item = await db.get(Item, item_id)
    return item

# создать новый товар
async def create_item(
    db: AsyncSession,
    name: str,
    description: str | None,
    price: float,
    in_stock: bool = True,
) -> Item:
    item = Item(
        name=name,
        description=description,
        price=price,
        in_stock=in_stock,
    )
    db.add(item)
    await db.commit()
    return item

# обновить товар по ID
async def update_item(db: AsyncSession, item_id: int, **fields) -> Item | None:
    item = await db.get(Item, item_id)
    if not item:
        return None

    for key, value in fields.items():
        setattr(item, key, value)
        
    return item

# удалить товар по ID
async def delete_item(db: AsyncSession, item_id: int) -> bool:
    item = await db.get(Item, item_id)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True