from sqlmodel.ext.asyncio.session import AsyncSession

from app.access import AccessUser
from app.models.users import User, UserUpdate
from app.repositories.users import get_user_by_username, update_user


async def get_me(current_user: AccessUser) -> User:
    '''
    Вернуть данные текущего авторизованного пользователя.
    '''
    return current_user.user


async def patch_me(
    session: AsyncSession,
    current_user: AccessUser,
    user_in: UserUpdate
) -> User:
    '''
    Обновить данные текущего пользователя по присланным полям,
    с проверкой уникальности username перед сохранением.
    '''
    if user_in.username:
        existing_user = await get_user_by_username(
            session=session, 
            username=user_in.username
        )
        if existing_user and existing_user.id != current_user.user.id:
            raise ValueError("Username already exists")
    
    db_user = await session.get(User, current_user.user.id)
    
    return await update_user(
        session=session,
        db_user=db_user,
        user_in=user_in
    )