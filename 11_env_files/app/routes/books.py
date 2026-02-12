from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.database import SessionDep
from app.models.books import BookCreate, BookOut, BookUpdate
from app.repositories.books import (
    create_book as create_book_repo,
    delete_book as delete_book_repo,
    get_book as get_book_repo,
    update_book as update_book_repo,
)

router = APIRouter(prefix="/books", tags=["Books"])
@router.post("", response_model=BookOut)
async def create_book(payload: BookCreate, session: SessionDep):
    return await create_book_repo(session, payload)


@router.get("/{book_id}", response_model=BookOut)
async def get_book(book_id: UUID, session: SessionDep):
    book = await get_book_repo(session, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.patch("/{book_id}", response_model=BookOut)
async def update_book(book_id: UUID, payload: BookUpdate, session: SessionDep):
    book_db = await get_book_repo(session, book_id)
    if book_db is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return await update_book_repo(session, book_db, payload)


@router.delete("/{book_id}")
async def delete_book(book_id: UUID, session: SessionDep):
    book_db = await get_book_repo(session, book_id)
    if book_db is None:
        raise HTTPException(status_code=404, detail="Book not found")

    await delete_book_repo(session, book_db)
    return {"status": "deleted"}
