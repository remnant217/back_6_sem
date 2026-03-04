import asyncio

from sqlmodel import select

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models import items
from app.models.roles import Role, RoleName, UserRoleLink
from app.models.users import User, UserCreate
from app.repositories.users import create_user

async def create_roles_and_admin():
    if not settings.FIRST_ADMIN_USERNAME or not settings.FIRST_ADMIN_PASSWORD:
        raise SystemExit("FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD are not set in .env")
    
    async with AsyncSessionLocal() as session:
        roles = (await session.exec(select(Role))).all()
        roles_by_name = {r.name for r in roles}

        if RoleName.USER.value not in roles_by_name:
            session.add(
                Role(name=RoleName.USER.value, description="Default user role")
            )
        if RoleName.ADMIN.value not in roles_by_name:
            session.add(
                Role(name=RoleName.ADMIN.value, description="Admin role")
            ) 

        await session.commit()

        role_admin = (
            await session.exec(select(Role).where(Role.name == RoleName.ADMIN.value))
        ).one()

        admin_user = (
            await session.exec(
                select(User).where(User.username == settings.FIRST_ADMIN_USERNAME)
            )
        ).first()

        if admin_user is None:
            admin_in = UserCreate(
                username=settings.FIRST_ADMIN_USERNAME,
                password=settings.FIRST_ADMIN_PASSWORD
            )
            admin_user = await create_user(session=session, user_data=admin_in)
        
        link = (await session.exec(
            select(UserRoleLink).where(
                (UserRoleLink.user_id == admin_user.id) &
                (UserRoleLink.role_id == role_admin.id)
            )
        )).first()

        if link is None:
            session.add(UserRoleLink(user_id=admin_user.id, role_id=role_admin.id))
            await session.commit()


if __name__ == "__main__":
    asyncio.run(create_roles_and_admin())