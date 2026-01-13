from fastapi import APIRouter, Depends, HTTPException

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
@router.get('/', response_model=list[ItemOut])
# Баг № 5 (во всех эндпоинтах) - неправильное использование SessionDep
# Баг № 6 - ингнорируется параметр q и нет response_model
async def list_items(db: SessionDep, q: str | None = None):
    items = await list_items_db(db, q)
    return items

# вернуть один товар по ID
# Баг № 7 - item_id и id, отсутствие статуса 404 и response_model
@router.get('/{item_id}', response_model=ItemOut, status_code=201)
async def get_item(item_id: int, db: SessionDep):
    item = await get_item_db(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail='Товар не найден',
        )
    return item

# создать новый товар
@router.post('/', response_model=ItemOut, status_code=201)
# Баг № 8 - игнорируется параметр in_stock
async def create_item(item: ItemCreate, db: SessionDep):
    new_item = await create_item_db(
        db,
        name=item.name,
        description=item.description,
        price=item.price,
        in_stock=item.in_stock,  
    )
    return new_item

# полное или частичное обновление товара
# Баг № 9 - отсутствие статуса 404 и response_model 
@router.patch('/{item_id}', response_model=ItemOut)
async def update_item(item_id: int, item: ItemUpdate, db: SessionDep):
    data = item.model_dump(exclude_unset=True)
    updated = await update_item_db(db, item_id, **data)
    if updated is None:
        raise HTTPException(status_code=404, detail='Товар не найден')
    return updated

# удалить товар
# Баг № 10 - отсутствие статуса 404, сомнительный формат ответа
@router.delete('/{item_id}', status_code=204)
async def delete_item(item_id: int, db: SessionDep):
    success = await delete_item_db(db, item_id)
    if not success:
        raise HTTPException(status_code=404, detail='Товар не найден')