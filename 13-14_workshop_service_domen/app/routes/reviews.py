from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.database import SessionDep
from app.models.reviews import ReviewCreate, ReviewOut, ReviewsOut, ReviewUpdate
from app.services.reviews import review_service, ValidationServiceError


router = APIRouter(tags=["Reviews"])


@router.post("/books/{book_id}/reviews", response_model=ReviewOut)
async def create_review(book_id: UUID, payload: ReviewCreate, session: SessionDep):
    try:
        review = await review_service.create(session, book_id, payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if review is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return review


@router.get("/reviews", response_model=ReviewsOut)
async def list_reviews(session: SessionDep, limit: int = 50, offset: int = 0):
    reviews, count = await review_service.list_with_count(session=session, limit=limit, offset=offset)
    return {"data": reviews, "count": count}


@router.get("/reviews/{review_id}", response_model=ReviewOut)
async def get_review_by_id(review_id: UUID, session: SessionDep):
    review = await review_service.get(session, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.get("/books/{book_id}/reviews", response_model=ReviewsOut)
async def list_reviews_by_book(book_id: UUID, session: SessionDep, limit: int = 50, offset: int = 0):
    reviews, count = await review_service.list_with_count(session=session, book_id=book_id, limit=limit, offset=offset)
    return {"data": reviews, "count": count}


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(review_id: UUID, payload: ReviewUpdate, session: SessionDep):
    try:
        review = await review_service.update(session=session, review_id=review_id, payload=payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: UUID, session: SessionDep):
    ok = await review_service.delete(session, review_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"status": "deleted"}
