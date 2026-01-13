from fastapi import APIRouter, Depends

from app.models import ItemCreate, ItemUpdate, ItemOut
from app.database import (
    SessionDep,
    list_items as list_items_db,
    get_item as get_item_db,
    create_item as create_item_db,
    update_item as update_item_db,
    delete_item as delete_item_db,
)

router = APIRouter(prefix='/items', tags=['items'])

# вернуть список товаров
@router.get('/')
async def list_items(q: str | None = None, db: SessionDep = Depends(SessionDep)):
    items = await list_items_db(db)
    return items

# вернуть один товар по ID
@router.get('/{item_id}')
async def get_item(id: int, db: SessionDep = Depends(SessionDep)):
    item = await get_item_db(db, id)
    if item is None:
        return {}
    return item

# создать новый товар
@router.post('/')
async def create_item(item: ItemCreate, db: SessionDep = Depends(SessionDep)):
    new_item = await create_item_db(
        db,
        name=item.name,
        description=item.description,
        price=item.price,
        in_stock=False,  
    )
    return new_item

# полное или частичное обновление товара
@router.patch('/{item_id}')
async def update_item(item_id: int, item: ItemUpdate, db: SessionDep = Depends(SessionDep)):
    data = item.model_dump(exclude_unset=True)
    updated = await update_item_db(db, item_id, **data)
    return updated

# удалить товар
@router.delete('/{item_id}')
async def delete_item(item_id: int, db: SessionDep = Depends(SessionDep)):
    success = await delete_item_db(db, item_id)
    if not success:
        return {'ok': False}
    return {'ok': True}