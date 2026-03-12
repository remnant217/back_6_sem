from fastapi import APIRouter

from app.api.v1.books import router as books_router
from app.api.v1.reviews import router as reviews_router

router = APIRouter()
router.include_router(books_router)
router.include_router(reviews_router)