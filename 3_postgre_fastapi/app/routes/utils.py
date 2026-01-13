from fastapi import HTTPException, APIRouter
from sqlalchemy import text
from app.database import SessionDep

router = APIRouter(prefix="/utils", tags=["utils"])

@router.get("/check-db")
async def check_db(db: SessionDep):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "OK"}
    except Exception:
        raise HTTPException(status_code=503, detail="База данных недоступна")