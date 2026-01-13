from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users import User, UserCreate

async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    new_user = User(**user_data.model_dump())
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)

async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()