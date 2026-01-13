from fastapi import FastAPI
from app.routes import router
from app.database import init_db

app = FastAPI()

# инициализируем базу данных при запуске приложения
init_db()

# подключаем роутер с эндпоинтами /items
app.include_router(router)