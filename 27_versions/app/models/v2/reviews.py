from sqlmodel import SQLModel

# делаем повторный импорт моделей без изменений, чтобы в V2-версии API
# обращаться только к V2-моделям
from app.models.reviews import (
    ReviewCreate,
    ReviewUpdate,
    ReviewOut,
    ReviewDB,
)


class PageMeta(SQLModel):
    """
    Метаданные параметров пагинации offset/limit.

    next_offset / prev_offset - подсказки клиенту:
    - next_offset: с какого offset загрузить следующую страницу (или None, если страницы нет)
    - prev_offset: с какого offset загрузить предыдущую страницу (или None, если страницы нет)
    """
    count: int
    limit: int
    offset: int
    next_offset: int | None = None
    prev_offset: int | None = None


class ReviewsOut(SQLModel):
    """
    Изменения в V2: вместо data/count используем items/metadata
    """
    items: list[ReviewOut]
    metainfo: PageMeta