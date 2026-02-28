from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.tokens import TokenPayload
from app.models.users import User
from app.access import AccessUser


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


SCOPES: dict[str, str] = {
    "items:read:own": "Чтение только своих items",
    "items:write:own": "Создание/изменение/удаление только своих items",
    "items:read:any": "Чтение items у любых пользователей",
    "items:write:any": "Создание/изменение/удаление items любых пользователей и смена владельца",

    "users:read:own": "Чтение только своих данных",
    "users:write:own": "Изменение только своих данных",
    "users:read:any": "Чтение данных любых пользователей",
    "users:write:any": "Создание/изменение/удаление любых пользователей"

}

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/login/access-token",
    scopes=SCOPES
)

TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(
    session: SessionDep,
    security_scopes: SecurityScopes,
    token: TokenDep
) -> AccessUser:
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = f"Bearer"
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value}
    )

    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise credentials_exception
    if not token_data.sub:
        raise credentials_exception
    
    token_scopes = token_data.scope.split()
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=401,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value}
            )
        
    user = await session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return AccessUser(user=user, scopes=token_scopes)