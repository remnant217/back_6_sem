from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.database import SessionDep
from app.services.books import book_service, ValidationServiceError
# указываем экспорт моделей из v2 для единообразия и удобства
from app.models.v2.books import (
    BookCreate,
    BookUpdate,
    BookOut,
    BooksOut,
    BookGenre,
    PageMeta,
)

# указываем тэг v2
router = APIRouter(prefix="/books", tags=["Books v2"])


@router.post("", response_model=BookOut)
async def create_book(payload: BookCreate, session: SessionDep):
    try:
        book = await book_service.create(session, payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return BookOut.model_validate(book, from_attributes=True)


@router.get("/{book_id}", response_model=BookOut)
async def get_book(book_id: UUID, session: SessionDep):
    book = await book_service.get(session, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookOut.model_validate(book, from_attributes=True)


@router.get("", response_model=BooksOut)
async def list_books(
    session: SessionDep,
    q: str | None = None,
    genre: BookGenre | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = Query(default=50, ge=1, le=200, description="Количество записей на странице"),
    offset: int = Query(default=0, ge=0, description="Сколько записей пропустить"),
):
    try:
        books, count = await book_service.list_with_count(
            session=session,
            q=q,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            limit=limit,
            offset=offset,
        )
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # добавляем вычисление параметров next_offset и prev_offset
    next_offset = offset + limit if (offset + limit) < count else None
    prev_offset = offset - limit if (offset - limit) >= 0 else None
    # складываем все книги в отдельный список
    items = [BookOut.model_validate(b, from_attributes=True) for b in books]
    # возвращаем BooksOut по версии v2
    return BooksOut(
        items=items,
        metainfo=PageMeta(
            count=count,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
            prev_offset=prev_offset,
        ),
    )


@router.patch("/{book_id}", response_model=BookOut)
async def update_book(book_id: UUID, payload: BookUpdate, session: SessionDep):
    try:
        book = await book_service.update(session, book_id, payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookOut.model_validate(book, from_attributes=True)


@router.delete("/{book_id}")
async def delete_book(book_id: UUID, session: SessionDep):
    ok = await book_service.delete(session, book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"status": "deleted"}