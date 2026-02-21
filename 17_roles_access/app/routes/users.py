from uuid import UUID

from fastapi import HTTPException, APIRouter, Query

from app.deps import SessionDep
from app.models.users import UserCreate, UserOut, UsersOut, UserUpdate, User
from app.repositories.users import (
    get_user, 
    create_user as create_user_repository, 
    delete_user,
    list_users_with_count,
    get_user_by_username,
    update_user
)
from app.models.items import ItemCreate, ItemOut, ItemsOut
from app.repositories.items import create_item as create_item_repository, list_items_with_count

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserOut)
async def create_user(user: UserCreate, session: SessionDep):
    return await create_user_repository(session, user)


@router.post('/{user_id}/items')
async def create_user_item(user_id: UUID, item_data: ItemCreate, session: SessionDep):
    user = await get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    new_item = await create_item_repository(session=session, user=user, item_data=item_data)
    return new_item


@router.get("/", response_model=UsersOut)
async def read_users(
    session: SessionDep,
    q: str | None = Query(default=None, description="Поиск по username"),
    is_active: bool | None = Query(default=None, description="Фильтр активности"),
    limit: int = Query(default=20, ge=1, le=100, description="Количество записей на странице"),
    offset: int = Query(default=0, ge=0, description="Сколько записей пропустить")
):
    users, count = await list_users_with_count(session, q, is_active, limit, offset)
    return UsersOut(data=users, count=count)


@router.get("/{user_id}", response_model=UserOut)
async def get_user_by_id(user_id: UUID, session: SessionDep):
    user = await get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get('/{user_id}/items', response_model=ItemsOut)
async def get_user_items(
    user_id: UUID,
    session: SessionDep,
    q: str | None = Query(default=None, description='Поиск по названию'),
    limit: int = Query(default=20, ge=1, le=100, description='Количество записей на странице'),
    offset: int = Query(default=0, ge=0, description='Сколько записей пропустить') 
):
    user = await get_user(session=session, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    
    items, count = await list_items_with_count(
        session=session,
        q=q,
        limit=limit,
        offset=offset,
        user_id=user_id
    )

    return ItemsOut(data=items, count=count)


@router.patch('/{user_id}', response_model=UserOut)
async def patch_user(user_id: UUID, user_in: UserUpdate, session: SessionDep):
    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')
    
    if user_in.username:
        existing_user = await get_user_by_username(session, user_in.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=409, detail='Username already exists')
    
    db_user = await update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}")
async def delete_user_by_id(user_id: UUID, session: SessionDep):
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await delete_user(session, user)
    return {"status": "deleted"}