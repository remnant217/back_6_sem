from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.items import Item, ItemCreate

async def create_item(session: AsyncSession, user_id: UUID, item_data: ItemCreate):
    new_item = Item(**item_data.model_dump(), user_id=user_id)
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

async def delete_item(session: AsyncSession, item: Item):
    await session.delete(item)
    await session.commit()



    