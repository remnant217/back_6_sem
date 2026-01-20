from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.models.items import ItemOut
from app.repositories.items import get_item, delete_item

router = APIRouter(prefix='/items', tags=['items'])

@router.get('/{item_id}', response_model=ItemOut)
async def read_item_by_id(item_id: UUID, session: SessionDep):
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    return item

@router.delete('/{item_id}')
async def delete_item_by_id(item_id: UUID, session: SessionDep):
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    await delete_item(session=session, item=item)
    return {'status': 'deleted'}
    