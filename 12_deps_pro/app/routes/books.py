from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.database import SessionDep
from app.models.books import BookCreate, BookOut, BookUpdate, BookGenre
from app.services.books import book_service
from app.services.books import ValidationServiceError

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("", response_model=BookOut)
async def create_book(payload: BookCreate, session: SessionDep):
    try:
        return await book_service.create(session, payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{book_id}", response_model=BookOut)
async def get_book(book_id: UUID, session: SessionDep):
    book = await book_service.get(session, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("")
async def list_books(
    session: SessionDep,
    q: str | None = None,
    genre: BookGenre | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 50,
    offset: int = 0,
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

    return {"data": books, "count": count}


@router.patch("/{book_id}", response_model=BookOut)
async def update_book(book_id: UUID, payload: BookUpdate, session: SessionDep):
    try:
        book = await book_service.update_book(session, book_id, payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/{book_id}")
async def delete_book(book_id: UUID, session: SessionDep):
    ok = await book_service.delete(session, book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"status": "deleted"}