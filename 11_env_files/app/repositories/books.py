from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.books import BookCreate, BookDB, BookUpdate


async def create_book(session: AsyncSession, data: BookCreate) -> BookDB:
    book = BookDB(**data.model_dump())
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book


async def get_book(session: AsyncSession, book_id: UUID) -> BookDB | None:
    result = await session.exec(select(BookDB).where(BookDB.id == book_id))
    return result.first()


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