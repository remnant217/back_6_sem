from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.access import AccessUser
from app.models.items import Item, ItemUpdate, ItemCreate
from app.models.users import User
from app.repositories import items as items_repo
from app.repositories import users as users_repo


async def create_item(
    session: AsyncSession,
    current_user: AccessUser,
    item_data: ItemCreate
) -> Item:
    '''
    Создать новый item для текущего пользователя.
    '''
    owner = await session.get(User, current_user.user.id)
    return await items_repo.create_item(
        session=session,
        user=owner,
        item_data=item_data
    )


async def get_items_with_count(
    session: AsyncSession,
    current_user: AccessUser,
    q: str | None,
    limit: int,
    offset: int
) -> tuple[list[Item], int]:
    '''
    Вернуть список items и общее количество записей с учетом прав: 
    user получает только свои items, admin - все.
    '''

    # есть ли "any" в scopes (да - admin, нет - user)
    if current_user.can("items", "read"):
        user_id = None
    else:
        user_id = current_user.user.id
    
    return await items_repo.list_items_with_count(
        session=session,
        q=q,
        user_id=user_id,
        limit=limit,
        offset=offset
    )


async def get_item_for_read(
    session: AsyncSession,
    current_user: AccessUser,
    item_id: UUID
) -> Item | None:
    '''
    Получить item по id, но вернуть None, если доступ запрещен
    (user не должен знать о существовании чужих item).
    '''
    item = await items_repo.get_item(session=session, item_id=item_id)
    if item is None:
        return None
    
    if current_user.can("items", "read", owner_id=item.user_id):
        return item
    
    return None


async def get_item_for_write(
    session: AsyncSession,
    current_user: AccessUser,
    item_id: UUID
) -> Item | None:
    '''
    Получить item по id для изменения/удаления, 
    но вернуть None, если нет прав на изменение 
    (user может менять только свои item, admin - любые).
    '''
    item = await items_repo.get_item(session=session, item_id=item_id)
    if item is None:
        return None
    
    if current_user.can("items", "write", owner_id=item.user_id):
        return item
    
    return None


async def patch_item(
    session: AsyncSession,
    item_db: Item,
    item_data: ItemUpdate
) -> Item:
    '''
    Обновить поля item (без смены владельца), предполагая, 
    что доступ уже проверен через get_item_for_write().
    '''
    return await items_repo.patch_item(
        session=session,
        item_db=item_db,
        item_data=item_data,
        new_user=None
    )


async def delete_item(
    session: AsyncSession,
    item_db: Item
) -> None:
    '''
    Удалить item, предполагая, что доступ уже проверен через get_item_for_write().
    '''
    await items_repo.delete_item(session=session, item=item_db)


async def change_item_owner(
    session: AsyncSession,
    current_user: AccessUser,
    item_id: UUID,
    new_owner_id: UUID
) -> Item | None:
    '''
    Админская операция: сменить владельца item на другого пользователя 
    (возвращает None, если item не найден)
    '''
    # доп. защита на уровне сервиса
    if not current_user.can("items", "write"):
        return None
    
    item = await items_repo.get_item(session=session, item_id=item_id)
    if item is None:
        return None
    
    new_owner = await users_repo.get_user(session=session, user_id=new_owner_id)
    if new_owner is None:
        return None
    
    # используем репозиторий, где уже есть логика смены владельца через new_user
    return await items_repo.patch_item(
        session=session,
        item_db=item,
        # кладем пустой ItemUpdate, т.к. у нас только смена владельца
        item_data=ItemUpdate(),
        new_user=new_owner
    )