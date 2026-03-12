from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.books import BookDB


class ReviewBase(SQLModel):
    rating: int = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=2000)


class ReviewCreate(ReviewBase):
    pass


class ReviewOut(ReviewBase):
    id: UUID
    book_id: UUID


class ReviewUpdate(SQLModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, max_length=2000)


class ReviewsOut(SQLModel):
    data: list[ReviewOut]
    count: int


class ReviewDB(ReviewBase, table=True):
    __tablename__ = "reviews"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    book_id: UUID = Field(foreign_key="books.id", nullable=False, ondelete="CASCADE")

    book: "BookDB" = Relationship(back_populates="reviews")