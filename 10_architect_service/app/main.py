from fastapi import FastAPI

from app.routes.books import router as books_router
from app.routes.utils import router as utils_router

app = FastAPI()

app.include_router(utils_router)
app.include_router(books_router)
