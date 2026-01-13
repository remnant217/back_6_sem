from fastapi import FastAPI
from app.routes.users import router as users_router
from app.routes.utils import router as utils_router

app = FastAPI()

app.include_router(users_router)
app.include_router(utils_router)