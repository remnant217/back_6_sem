from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.database import SessionDep
from app.domain.book import BookGenre, InvalidYearError
from app.models.books import BookCreate, BookOut, BookUpdate, BooksOut
from app.repositories import books as repo

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, session: SessionDep):
    try:
        return await repo.create_book(session, book)
    except InvalidYearError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=BooksOut)
async def list_books(
    session: SessionDep,
    q: str | None = Query(default=None, description="Поиск по title/author"),
    genre: BookGenre | None = Query(default=None, description="Жанр"),
    author: str | None = Query(default=None, description="Фильтр по автору"),
    year_from: int | None = Query(default=None, ge=1000, description="Год издания от"),
    year_to: int | None = Query(default=None, le=2100, description="Год издания до"),
    limit: int = Query(default=20, ge=1, le=100, description="Размер страницы"),
    offset: int = Query(default=0, ge=0, description="Сколько пропустить"),
):
    books, count = await repo.list_books_with_count(
        session,
        q=q,
        genre=genre,
        author=author,
        year_from=year_from,
        year_to=year_to,
        limit=limit,
        offset=offset,
    )
    return BooksOut(data=books, count=count)


@router.get("/{book_id}", response_model=BookOut)
async def get_book(book_id: int, session: SessionDep):
    book = await repo.get_book(session, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookOut)
async def update_book(book_id: int, book_in: BookUpdate, session: SessionDep):
    db_book = await repo.get_book(session, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        return await repo.update_book(session, db_book, book_in)
    except InvalidYearError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, session: SessionDep):
    db_book = await repo.get_book(session, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    await repo.delete_book(session, db_book)
    return None
