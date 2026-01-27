'''
АГ
Разделил строчки по логике работы и убрал создание лишнего роутера,
у нас же есть уже books_router, его сразу и подключаем к app.
'''

from fastapi import FastAPI
from app.routes.books import router as books_router

app = FastAPI(title="Books API")

app.include_router(books_router)