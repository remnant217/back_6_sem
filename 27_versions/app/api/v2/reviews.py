from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.database import SessionDep
from app.services.reviews import review_service, ValidationServiceError
# указываем экспорт моделей из v2 для единообразия и удобства
from app.models.v2.reviews import (
    ReviewCreate,
    ReviewUpdate,
    ReviewOut,
    ReviewsOut,
    PageMeta,
)

# указываем тэг v2
router = APIRouter(tags=["Reviews v2"])


@router.post("/books/{book_id}/reviews", response_model=ReviewOut)
async def create_review(book_id: UUID, payload: ReviewCreate, session: SessionDep):
    try:
        review = await review_service.create(session, book_id, payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if review is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return ReviewOut.model_validate(review, from_attributes=True)


@router.get("/reviews", response_model=ReviewsOut)
async def list_reviews(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200, description="Количество записей на странице"),
    offset: int = Query(default=0, ge=0, description="Сколько записей пропустить"),
):
    reviews, count = await review_service.list_with_count(session=session, limit=limit, offset=offset)

    next_offset = offset + limit if (offset + limit) < count else None
    prev_offset = offset - limit if (offset - limit) >= 0 else None

    items = [ReviewOut.model_validate(r, from_attributes=True) for r in reviews]

    return ReviewsOut(
        items=items,
        metainfo=PageMeta(
            count=count,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
            prev_offset=prev_offset,
        ),
    )


@router.get("/reviews/{review_id}", response_model=ReviewOut)
async def get_review_by_id(review_id: UUID, session: SessionDep):
    review = await review_service.get(session, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewOut.model_validate(review, from_attributes=True)


@router.get("/books/{book_id}/reviews", response_model=ReviewsOut)
async def list_reviews_by_book(
    book_id: UUID,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    reviews, count = await review_service.list_with_count(session=session, book_id=book_id, limit=limit, offset=offset)
    # добавляем вычисление параметров next_offset и prev_offset
    next_offset = offset + limit if (offset + limit) < count else None
    prev_offset = offset - limit if (offset - limit) >= 0 else None
    # складываем все отзывы в отдельный список
    items = [ReviewOut.model_validate(r, from_attributes=True) for r in reviews]
    # возвращаем ReviewsOut по версии v2
    return ReviewsOut(
        items=items,
        metainfo=PageMeta(
            count=count,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
            prev_offset=prev_offset,
        ),
    )


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(review_id: UUID, payload: ReviewUpdate, session: SessionDep):
    try:
        review = await review_service.update(session=session, review_id=review_id, payload=payload)
    except ValidationServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewOut.model_validate(review, from_attributes=True)


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: UUID, session: SessionDep):
    ok = await review_service.delete(session, review_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"status": "deleted"}