from uuid import UUID

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.items import Item, ItemCreate, ItemUpdate
from app.models.users import User


def _apply_items_filters(stmt, q: str | None, user_id: UUID | None):
    if user_id is not None:
        stmt = stmt.where(Item.user_id == user_id)
    if q:
        q = q.strip()
        if q:
            stmt = stmt.where(Item.title.ilike(f'%{q}%'))
    return stmt


async def create_item(session: AsyncSession, user: User, item_data: ItemCreate):
    new_item = Item(**item_data.model_dump(), user=user)
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return new_item


async def get_item(session: AsyncSession, item_id: UUID) -> Item | None:
    return await session.get(Item, item_id)


async def list_items_with_count(
    session: AsyncSession,
    q: str | None,
    user_id: UUID | None,
    limit: int,
    offset: int
) -> tuple[list[Item], int]:
    data_stmt = select(Item)
    data_stmt = _apply_items_filters(stmt=data_stmt, q=q, user_id=user_id)
    data_stmt = data_stmt.order_by(Item.title)
    data_stmt = data_stmt.offset(offset).limit(limit)

    data_result = await session.exec(data_stmt)
    items = data_result.all()

    count_stmt = select(func.count()).select_from(Item)
    count_stmt = _apply_items_filters(stmt=count_stmt, q=q, user_id=user_id)

    count_result = await session.exec(count_stmt)
    count = count_result.one()

    return items, count


async def patch_item(
    session: AsyncSession,
    item_db: Item,
    item_data: ItemUpdate,
    new_user: User | None = None
) -> Item:
    if new_user is not None:
        item_db.user = new_user
    data = item_data.model_dump(exclude_unset=True, exclude={'user_id'})
    item_db.sqlmodel_update(data)
    session.add(item_db)
    await session.commit()
    await session.refresh(item_db)
    return item_db


async def delete_item(session: AsyncSession, item: Item):
    await session.delete(item)
    await session.commit()