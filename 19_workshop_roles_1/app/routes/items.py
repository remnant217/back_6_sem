from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Security

from app.deps import SessionDep, get_current_user
from app.models.items import ItemOut, ItemUpdate, ItemsOut
from app.repositories.items import get_item, delete_item, patch_item, list_items_with_count
from app.repositories.users import get_user
from app.access import AccessUser

router = APIRouter(prefix='/items', tags=['items'])


@router.get('/', response_model=ItemsOut)
async def read_items(
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:own"])],
    q: str | None = Query(default=None, description='Поиск по названию'),
    limit: int = Query(default=20, ge=1, le=100, description='Количество записей на странице'),
    offset: int = Query(default=0, ge=0, description='Сколько записей пропустить')
):
    items, count = await list_items_with_count(
        session=session,
        q=q,
        limit=limit,
        offset=offset,
        user_id=None
    )

    return ItemsOut(data=items, count=count)


@router.get("/{item_id}", response_model=ItemOut) 
async def read_item_by_id(
    item_id: UUID, 
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:own"])]
):
    item = await get_item(session, item_id)
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
    item_db = await get_item(session, item_id)
    if item_db is None:
        raise HTTPException(status_code=404, detail='Item not found')
    
    payload = item_data.model_dump(exclude_unset=True)
    new_user = None

    if 'user_id' in payload:
        if item_data.user_id is None:
            raise HTTPException(status_code=422, detail='user_id cannot be null') 
        
        new_user = await get_user(session, item_data.user_id)
        if new_user is None:
            raise HTTPException(status_code=404, detail='User not found')
    
    updated_item = await patch_item(
        session=session,
        item_db=item_db,
        item_data=item_data,
        new_user=new_user
    )
    return updated_item


@router.delete("/{item_id}")
async def delete_item_by_id(
    item_id: UUID, 
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:own"])]
):
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    await delete_item(session=session, item=item)
    return {'status': 'deleted'}