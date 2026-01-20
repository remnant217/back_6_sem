from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.database import SessionDep

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get("/check-db")
async def check_db(session: SessionDep):
    try:
        await session.exec(select(1))
        return {"status": "OK"}
    except Exception:
        raise HTTPException(status_code=503, detail="База данных недоступна")
