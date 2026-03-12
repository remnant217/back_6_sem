from fastapi import FastAPI

from app.core.settings import settings
# подключаем middleware и новые роутеры
from app.core.middlewares import add_deprecation_headers
from app.api.v1.routers import router as v1_router
from app.api.v2.routers import router as v2_router

# контейнер для монтирования подприложений, без своей документации
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# базовый префикс API, берем из .env-файла
base_prefix = settings.API_PREFIX

# создаем подприложение для версии v1
app_v1 = FastAPI(title=f"{settings.APP_TITLE} (v1)")
app_v1.include_router(v1_router)

# добавляем заголовки Deprecation/Sunset на всю v1-версию
add_deprecation_headers(app_v1)

# создаем подприложение для версии v2
app_v2 = FastAPI(title=f"{settings.APP_TITLE} (v2)")
app_v2.include_router(v2_router)

# монтируем версии - сначала v2, затем v1, иначе v2 не будет видно

# v2 будет доступна по http://127.0.0.1:8000/api/v2/docs
app.mount(f"{base_prefix}/v2", app_v2) 
# v1 будет доступна по http://127.0.0.1:8000/api/docs
app.mount(base_prefix, app_v1)      