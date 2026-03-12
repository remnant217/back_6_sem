from sqlmodel import SQLModel

# делаем повторный импорт моделей без изменений, чтобы в V2-версии API
# обращаться только к V2-моделям
from app.models.books import (
    BookCreate,
    BookUpdate,
    BookOut,
    BookDB,
    BookGenre,
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


class BooksOut(SQLModel):
    """
    Изменения в v2: вместо data/count используем items/metadata
    """
    items: list[BookOut]
    metainfo: PageMeta