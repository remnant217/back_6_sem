from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.items import Item, ItemCreate, ItemUpdate
from app.models.users import User

async def create_item(session: AsyncSession, user: User, item_data: ItemCreate):
    new_item = Item(**item_data.model_dump(), user=user)
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return new_item

async def get_item(session: AsyncSession, item_id: UUID) -> Item | None:
    return await session.get(Item, item_id)

async def list_items_by_user_id(session: AsyncSession, user_id: UUID) -> list[Item]:
    stmt = select(Item).where(user_id == Item.user_id)
    result = await session.exec(stmt)
    return result.all()

async def patch_item(
    session: AsyncSession,
    item_db: Item,
    item_data: ItemUpdate,
    new_user: User | None = None
) -> Item:
    # обновляем связь через Relationship(), если передан новый владелец
    if new_user is not None:
        item_db.user = new_user
    # обновляем остальные поля, кроме user_id
    data = item_data.model_dump(exclude_unset=True, exclude={'user_id'})
    item_db.sqlmodel_update(data)

    session.add(item_db)
    await session.commit()
    await session.refresh(item_db)
    return item_db

async def delete_item(session: AsyncSession, item: Item):
    await session.delete(item)
    await session.commit()