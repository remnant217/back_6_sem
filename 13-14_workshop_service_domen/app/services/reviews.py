from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.reviews import Review, DomainError
from app.models.reviews import ReviewCreate, ReviewDB, ReviewUpdate
from app.repositories.reviews import (
    create_review,
    get_review,
    list_reviews_with_count,
    patch_review,
    delete_review,
)
from app.repositories.books import get_book


class ServiceError(Exception):
    """Базовая ошибка слоя приложения (services)."""


class ValidationServiceError(ServiceError):
    """Ошибка бизнес-валидации (пришло некорректное значение)."""


class ReviewService:
    async def create(self, session: AsyncSession, book_id: UUID, payload: ReviewCreate) -> ReviewDB | None:
        book = await get_book(session, book_id)
        if book is None:
            return None
        try:
            Review(id=None, book_id=book_id, rating=payload.rating, text=payload.text)
        except DomainError as e:
            raise ValidationServiceError(str(e)) from e

        return await create_review(session=session, book=book, data=payload)

    async def get(self, session: AsyncSession, review_id: UUID) -> ReviewDB | None:
        return await get_review(session, review_id)

    async def list_with_count(
        self, session: AsyncSession, book_id: UUID | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[ReviewDB], int]:
        return await list_reviews_with_count(session=session, book_id=book_id, limit=limit, offset=offset)

    async def update(self, session: AsyncSession, review_id: UUID, payload: ReviewUpdate) -> ReviewDB | None:
        review_db = await get_review(session, review_id)
        if review_db is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        final_rating = data.get("rating", review_db.rating)
        final_text = data.get("text", review_db.text)
        try:
            Review(id=review_db.id, book_id=review_db.book_id, rating=final_rating, text=final_text)
        except DomainError as e:
            raise ValidationServiceError(str(e)) from e
        return await patch_review(session=session, review_db=review_db, data=payload)

    async def delete(self, session: AsyncSession, review_id: UUID) -> bool:
        review = await get_review(session, review_id)
        if review is None:
            return False
        await delete_review(session, review)
        return True


review_service = ReviewService()