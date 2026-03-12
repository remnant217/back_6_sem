from fastapi import APIRouter

from app.api.v2.books import router as books_router
from app.api.v2.reviews import router as reviews_router

router = APIRouter()
router.include_router(books_router)
router.include_router(reviews_router)