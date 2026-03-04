from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Security

from app.deps import SessionDep, get_current_user
from app.models.items import ItemOut, ItemUpdate, ItemsOut, ItemOwnerUpdate, ItemCreate
from app.services import items as items_service
from app.access import AccessUser

router = APIRouter(prefix='/items', tags=['items'])


@router.post('/', response_model=ItemOut)
async def create_item(
    item_data: ItemCreate,
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:own"])]
):
    return await items_service.create_item(
        session=session,
        current_user=current_user,
        item_data=item_data
    )


@router.get('/', response_model=ItemsOut)
async def read_items(
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:own"])],
    q: str | None = Query(default=None, description='Поиск по названию'),
    limit: int = Query(default=20, ge=1, le=100, description='Количество записей на странице'),
    offset: int = Query(default=0, ge=0, description='Сколько записей пропустить')
):
    items, count = await items_service.get_items_with_count(
        session=session,
        current_user=current_user,
        q=q,
        limit=limit,
        offset=offset
    )

    return ItemsOut(data=items, count=count)


@router.get("/{item_id}", response_model=ItemOut) 
async def read_item_by_id(
    item_id: UUID, 
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:own"])]
):
    item = await items_service.get_item_for_read(
        session=session,
        current_user=current_user,
        item_id=item_id
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    return item


@router.patch("/{item_id}", response_model=ItemOut) 
async def patch_item_by_id(
    item_id: UUID, 
    item_data: ItemUpdate, 
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:own"])]
):
    item_db = await items_service.get_item_for_write(
        session=session,
        current_user=current_user,
        item_id=item_id
    )
    if item_db is None:
        raise HTTPException(status_code=404, detail='Item not found')
    
    updated_item = await items_service.patch_item(
        session=session,
        item_db=item_db,
        item_data=item_data
    )
    return updated_item


@router.patch("/{item_id}/owner", response_model=ItemOut)
async def change_item_owner(
    item_id: UUID,
    owner_data: ItemOwnerUpdate,
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:any"])]
):
    updated = await items_service.change_item_owner(
        session=session,
        current_user=current_user,
        item_id=item_id,
        new_owner_id=owner_data.user_id
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return updated


@router.delete("/{item_id}")
async def delete_item_by_id(
    item_id: UUID, 
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:own"])]
):
    item_db = await items_service.get_item_for_write(
        session=session,
        current_user=current_user,
        item_id=item_id
    )
    if item_db is None:
        raise HTTPException(status_code=404, detail='Item not found')
    
    await items_service.delete_item(session=session, item_db=item_db)
    return {"status": "deleted"}