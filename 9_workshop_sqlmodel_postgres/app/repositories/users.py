from uuid import UUID

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.users import User, UserCreate, UserUpdate

# применяем указанные фильтры к запросу
def _apply_users_filters(stmt, q: str | None, is_active: bool | None):
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if q:
        q = q.strip()
        if q:
            stmt = stmt.where(User.username.ilike(f'%{q}%'))
    return stmt

# возвращаем список пользователей текущей страницы 
# и общее количество пользователей с учетом фильтрации
async def list_users_with_count(
    session: AsyncSession,      
    q: str | None,              
    is_active: bool | None,     
    limit: int,                 
    offset: int                 
) -> tuple[list[User], int]:
    
    data_stmt = select(User)
    data_stmt = _apply_users_filters(data_stmt, q, is_active)
    data_stmt = data_stmt.order_by(User.username)
    data_stmt = data_stmt.offset(offset).limit(limit)
    data_result = await session.exec(data_stmt)
    users = data_result.all()

    count_stmt = select(func.count()).select_from(User)
    count_stmt = _apply_users_filters(count_stmt, q, is_active)
    count_result = await session.exec(count_stmt)
    count = count_result.one()

    return users, count

async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    new_user = User(**user_data.model_dump())
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

# поиск пользователя по username
async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await session.exec(stmt)
    return result.first()

async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)

# частичное обновление данных пользователя
async def update_user(session: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
    user_data = user_in.model_dump(exclude_unset=True)
    db_user.sqlmodel_update(user_data)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()