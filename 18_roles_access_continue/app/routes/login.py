from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from app.core.config import settings
from app.core.security import create_access_token, scopes_for_roles
from app.deps import CurrentUser, SessionDep
from app.models.tokens import Token
from app.models.users import UserOut
from app.models.roles import Role, UserRoleLink
from app.repositories.users import authenticate_user

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/access-token", response_model=Token)
async def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    stmt_roles = (
        select(Role.name)
        .join(UserRoleLink, Role.id == UserRoleLink.role_id)
        .where(UserRoleLink.user_id == user.id)
    )
    role_names = (await session.exec(stmt_roles)).all()
    scopes_list = scopes_for_roles(role_names)
    scope_str = " ".join(scopes_list)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=create_access_token(
            subject=user.id, 
            expires_delta=access_token_expires,
            scope=scope_str
        )
    )


@router.post("/test-token", response_model=UserOut)
async def test_token(current_user: CurrentUser):
    return current_user