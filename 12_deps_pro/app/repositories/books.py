from uuid import UUID
from sqlmodel import func, select

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.books import BookCreate, BookDB, BookUpdate, BookGenre


def _apply_book_filters(
    stmt,
    q: str | None,
    genre: BookGenre | None,
    year_from: int | None,
    year_to: int | None,
):
    # Фильтр по жанру
    if genre is not None:
        stmt = stmt.where(BookDB.genre == genre)

    # Фильтр по диапазону года
    if year_from is not None:
        stmt = stmt.where(BookDB.published_year >= year_from)
    if year_to is not None:
        stmt = stmt.where(BookDB.published_year <= year_to)

    # Поиск по строке
    if q:
        q = q.strip()
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                (BookDB.title.ilike(like)) | (BookDB.author.ilike(like))
            )

    return stmt


async def create_book(session: AsyncSession, data: BookCreate) -> BookDB:
    book = BookDB(**data.model_dump())
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book


async def get_book(session: AsyncSession, book_id: UUID) -> BookDB | None:
    result = await session.exec(select(BookDB).where(BookDB.id == book_id))
    return result.first()


async def list_books_with_count(
    session: AsyncSession,
    q: str | None = None,
    genre: BookGenre | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[BookDB], int]:

    data_stmt = select(BookDB)
    data_stmt = _apply_book_filters(data_stmt, q, genre, year_from, year_to)
    data_stmt = data_stmt.order_by(BookDB.title).offset(offset).limit(limit)

    data_result = await session.exec(data_stmt)
    books = data_result.all()

    count_stmt = select(func.count()).select_from(BookDB)
    count_stmt = _apply_book_filters(count_stmt, q, genre, year_from, year_to)

    count_result = await session.exec(count_stmt)
    count = count_result.one()

    return books, count


async def update_book(session: AsyncSession, book_db: BookDB, data: BookUpdate) -> BookDB:
    patch = data.model_dump(exclude_unset=True)
    book_db.sqlmodel_update(patch)
    session.add(book_db)
    await session.commit()
    await session.refresh(book_db)
    return book_db


async def delete_book(session: AsyncSession, book_db: BookDB) -> None:
    await session.delete(book_db)
    await session.commit()