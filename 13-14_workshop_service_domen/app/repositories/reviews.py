from uuid import UUID

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.reviews import ReviewCreate, ReviewDB, ReviewUpdate
from app.models.books import BookDB


def _apply_review_filters(stmt, book_id: UUID | None = None):
    if book_id is not None:
        stmt = stmt.where(ReviewDB.book_id == book_id)
    return stmt


async def create_review(session: AsyncSession, book: BookDB, data: ReviewCreate) -> ReviewDB:
    review = ReviewDB(book=book, **data.model_dump())
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def get_review(session: AsyncSession, review_id: UUID) -> ReviewDB | None:
    result = await session.exec(select(ReviewDB).where(ReviewDB.id == review_id))
    return result.first()


async def list_reviews_with_count(
    session: AsyncSession,
    book_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ReviewDB], int]:
    data_stmt = select(ReviewDB)
    data_stmt = _apply_review_filters(data_stmt, book_id=book_id)
    data_stmt = data_stmt.order_by(ReviewDB.id).offset(offset).limit(limit)

    data_result = await session.exec(data_stmt)
    reviews = data_result.all()

    count_stmt = select(func.count()).select_from(ReviewDB)
    count_stmt = _apply_review_filters(count_stmt, book_id=book_id)

    count_result = await session.exec(count_stmt)
    count = count_result.one()

    return reviews, count


async def patch_review(session: AsyncSession, review_db: ReviewDB, data: ReviewUpdate) -> ReviewDB:
    patch = data.model_dump(exclude_unset=True)
    review_db.sqlmodel_update(patch)
    session.add(review_db)
    await session.commit()
    await session.refresh(review_db)
    return review_db


async def delete_review(session: AsyncSession, review_db: ReviewDB) -> None:
    await session.delete(review_db)
    await session.commit()
