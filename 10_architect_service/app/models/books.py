'''
АГ
1) Убрал работу с created_at и updated_at для простоты, можно добавить позже на курсе.
2) Переименовал Book в BookDB, чтобы не было конфликтом с доменной сущностью Book.
3) Для title max_length=500 заменил на max_length=200, чтобы совпадало с доменом.
4) Для published_year убрал le=2100, т.к. на уровне домена мы проверяем, 
что год не должен превышать текущий. Можно, конечно, добавить валидатор, но пока обойдемся
без него.
5) Для author max_length=300 заменил на max_length=120, чтобы совпадало с доменом.
6) Заменил тип id с int на UUID, мы с ним ранее уже работали и лучше его придерживаться.
'''

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.domain.book import BookGenre

class BookBase(SQLModel):
    """Базовая модель книги с общими полями"""
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    published_year: int = Field(ge=1000)
    genre: BookGenre
    description: str | None = Field(default=None, max_length=5000)
    page_count: int | None = Field(default=None, ge=1)


class BookCreate(BookBase):
    """Модель для создания книги"""
    pass


class BookUpdate(BookBase):
    """Модель для частичного обновления книги"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    published_year: int | None = Field(default=None, ge=1000)
    genre: BookGenre | None = None


class BookOut(BookBase):
    """Модель ответа для возвращения полей книги + ID"""
    id: UUID


class BooksOut(SQLModel):
    """Модель ответа для возвращения списка книг"""
    data: list[BookOut]
    count: int


class BookDB(BookBase, table=True):
    """ORM-модель таблицы books для хранения в БД"""
    __tablename__ = "books"

    id: UUID = Field(default_factory=uuid4, primary_key=True)