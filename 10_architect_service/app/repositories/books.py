from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.book import Book as DomainBook
from app.domain.book import BookGenre
from app.models.books import Book, BookCreate, BookUpdate


async def get_book(session: AsyncSession, book_id: int) -> Book | None:
    return await session.get(Book, book_id)


async def create_book(session: AsyncSession, book_in: BookCreate) -> Book:
    # Бизнес-логика: валидация года через domain
    DomainBook(
        id=None,
        title=book_in.title,
        author=book_in.author,
        published_year=book_in.published_year,
        genre=book_in.genre,
        description=book_in.description,
        page_count=book_in.page_count,
    )

    db_book = Book(**book_in.model_dump())
    session.add(db_book)
    await session.commit()
    await session.refresh(db_book)
    return db_book


async def update_book(session: AsyncSession, db_book: Book, book_in: BookUpdate) -> Book:
    data = book_in.model_dump(exclude_unset=True)

    new_year = data.get("published_year", db_book.published_year)
    DomainBook.validate_year(int(new_year))

    for k, v in data.items():
        setattr(db_book, k, v)

    db_book.updated_at = datetime.utcnow()

    session.add(db_book)
    await session.commit()
    await session.refresh(db_book)
    return db_book


async def delete_book(session: AsyncSession, db_book: Book) -> None:
    await session.delete(db_book)
    await session.commit()


async def list_books_with_count(
    session: AsyncSession,
    *,
    q: str | None = None,
    genre: BookGenre | None = None,
    author: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Book], int]:
    conditions = []

    if q:
        pattern = f"%{q}%"
        conditions.append(or_(col(Book.title).ilike(pattern), col(Book.author).ilike(pattern)))

    if genre:
        conditions.append(Book.genre == genre)

    if author:
        conditions.append(col(Book.author).ilike(f"%{author}%"))

    if year_from is not None:
        conditions.append(Book.published_year >= year_from)

    if year_to is not None:
        conditions.append(Book.published_year <= year_to)

    where_clause = and_(*conditions) if conditions else True

    count_stmt = select(func.count()).select_from(Book).where(where_clause)
    count_row = (await session.exec(count_stmt)).one()
    count = count_row[0] if isinstance(count_row, tuple) else count_row

    stmt = (
        select(Book)
        .where(where_clause)
        .order_by(Book.id)
        .offset(offset)
        .limit(limit)
    )
    books = (await session.exec(stmt)).all()
    return books, count
