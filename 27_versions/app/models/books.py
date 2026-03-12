from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

from app.domain.book import BookGenre

if TYPE_CHECKING:
    from app.models.reviews import ReviewDB


class BookBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    published_year: int = Field(ge=1000)
    genre: BookGenre
    description: str | None = Field(default=None, max_length=5000)
    page_count: int | None = Field(default=None, ge=1)


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    published_year: int | None = Field(default=None, ge=1000)
    genre: BookGenre | None = None


class BookOut(BookBase):
    id: UUID


class BooksOut(SQLModel):
    data: list[BookOut]
    count: int


class BookDB(BookBase, table=True):
    __tablename__ = "books"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    reviews: list["ReviewDB"] = Relationship(back_populates="book", passive_deletes="all")
