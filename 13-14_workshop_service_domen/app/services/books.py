from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.book import Book, BookGenre
from app.domain.book import DomainError
from app.models.books import BookCreate, BookUpdate, BookDB
from app.repositories.books import (
    create_book,
    get_book,
    update_book,
    delete_book,
    list_books_with_count,
)

class ServiceError(Exception):
    """Базовая ошибка слоя приложения (services)."""


class ValidationServiceError(ServiceError):
    """Ошибка бизнес-валидации (пришло некорректное значение)."""


class BookService:
    async def create(self, session: AsyncSession, data: BookCreate) -> BookDB:
        try:
            Book(
                id=None,
                title=data.title,
                author=data.author,
                published_year=data.published_year,
                genre=data.genre,
                description=data.description,
                page_count=data.page_count,
            )
        except DomainError as e:
            raise ValidationServiceError(str(e)) from e

        return await create_book(session, data)


    async def get(self, session: AsyncSession, book_id: UUID) -> BookDB | None:
        return await get_book(session, book_id)


    async def list_with_count(
        self,
        session: AsyncSession,
        q: str | None = None,
        genre: BookGenre | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BookDB], int]:
        return await list_books_with_count(
            session=session,
            q=q,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            limit=limit,
            offset=offset,
        )


    async def update(self, session: AsyncSession, book_id: UUID, data: BookUpdate) -> BookDB | None:
        book_db = await get_book(session, book_id)
        if book_db is None:
            return None

        payload = data.model_dump(exclude_unset=True)

        try:
            Book(
                id=book_db.id,
                title=payload.get("title", book_db.title),
                author=payload.get("author", book_db.author),
                published_year=payload.get("published_year", book_db.published_year),
                genre=payload.get("genre", book_db.genre),
                description=payload.get("description", book_db.description),
                page_count=payload.get("page_count", book_db.page_count),
            )
        except DomainError as e:
            raise ValidationServiceError(str(e)) from e

        return await update_book(session, book_db, data)


    async def delete(self, session: AsyncSession, book_id: UUID) -> bool:
        book_db = await get_book(session, book_id)
        if book_db is None:
            return False
        await delete_book(session, book_db)
        return True


book_service = BookService()