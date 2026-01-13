from fastapi import HTTPException, APIRouter

from app.database import SessionDep
from app.models.users import UserCreate, UserOut
from app.repositories.users import get_user, create_user as create_user_repository, delete_user

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserOut)
async def create_user(user: UserCreate, session: SessionDep):
    return await create_user_repository(session, user)

@router.get("/{user_id}", response_model=UserOut)
async def get_users_by_id(user_id: int, session: SessionDep):
    user = await get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
async def delete_user_by_id(user_id: int, session: SessionDep):
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await delete_user(session, user)
    return {"status": "deleted"}