from fastapi import FastAPI

# указываем дату, когда API перестанет работать
SUNSET = "Thu, 31 Dec 2026 23:59:59 GMT"


def add_deprecation_headers(app: FastAPI) -> None:
    """
    Добавляет заголовки Deprecation/Sunset ко всем ответам старого API (v1).
    Делается на уровне sub-app, чтобы не писать это в каждом файле с эндпоинтами.
    """
    @app.middleware("http")
    async def deprecation_middleware(request, call_next):
        response = await call_next(request)
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = SUNSET
        return response