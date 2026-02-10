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