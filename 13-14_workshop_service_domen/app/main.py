from fastapi import FastAPI

from app.core.settings import settings
from app.routes.books import router as books_router
from app.routes.reviews import router as reviews_router

app = FastAPI(title=settings.APP_TITLE)

app.include_router(books_router, prefix=settings.API_PREFIX)
app.include_router(reviews_router, prefix=settings.API_PREFIX)
