# Воркшоп. PostgreSQL и SQLModel

# Реализация репозиторных функций для GET /items и GET /users/{user_id}/items

'''
Итак, переходим к файлу app/repositories/items.py. Для реализации нужной логики
мы создадим новую функцию list_items_with_count() и вспомогательную функцию
_apply_items_filters() для описании логики фильтров. Так мы уже делали,
когда писали похожий код app/repositories/users.py.

Для начала посмотрим на импорты. У нас уже все есть, кроме специальной переменной func из sqlmodel,
она нам понадобится для реализации подсчета объектов.
'''

# app/repositories/items.py
...
from sqlmodel import select, func
...

'''
Далее пропишем заголовки наших функций. Пока что без тела, просто укажем сигнатуры,
так нам будет проще реализовывать тела функций:
'''

def _apply_items_filters(stmt, q: str | None, user_id: UUID | None):
    ...


async def list_items_with_count(
    session: AsyncSession,
    q: str | None,
    user_id: UUID | None,
    limit: int,
    offset: int
) -> tuple[list[Item], int]:
    ...

'''
Обратите внимание, что user_id мы сделали опциональным. Если передан None, то фильтр
по пользователю не применяется, значит работает GET /items. Если же передан UUID - 
значит работает GET /users/{user_id}/items.

Перейдем к реализации тела функции _apply_items_filters(). В нашем случае фильтры - 
это условия where, которые мы добавляем, если значение реально передано клиентом.
q - просто строка поиска, мы делаем strip(), чтобы q='  ' не превращалось
в бессмысленный запрос. q мы применяем для поиска по title. В будущем вы можете
расширить эту логику и добавить поиск по description 😎
'''

def _apply_items_filters(stmt, q: str | None, user_id: UUID | None):
    if user_id is not None:
        stmt = stmt.where(Item.user_id == user_id)
    if q:
        q = q.strip()
        if q:
            stmt = stmt.where(Item.title.ilike(f'%{q}%'))
    return stmt

'''
Далее реализуем тело функции list_items_with_count(), где будем собирать 2 объекта:
- data_stmt - выражение для получения списка объектов на конкретной странице, отсортированого по title
- count_stmt - выражение для получения общего количества объектов с учетом фильтрации
'''

async def list_items_with_count(
    session: AsyncSession,
    q: str | None,
    user_id: UUID | None,
    limit: int,
    offset: int
) -> tuple[list[Item], int]:
    data_stmt = select(Item)
    data_stmt = _apply_items_filters(stmt=data_stmt, q=q, user_id=user_id)
    data_stmt = data_stmt.order_by(Item.title)
    data_stmt = data_stmt.offset(offset).limit(limit)

    data_result = await session.exec(data_stmt)
    items = data_result.all()

    count_stmt = select(func.count()).select_from(Item)
    count_stmt = _apply_items_filters(stmt=count_stmt, q=q, user_id=user_id)

    count_result = await session.exec(count_stmt)
    count = count_result.one()

    return items, count

'''
Супер, теперь у нас есть универсальная функция репозитория, которая подходит для двух эндпоинтов.
Дальше мы будем ее использовать в эндпоинтах GET /items и GET /users/{user_id}/items.
Функцию list_items_by_user_id() пока что оставим, удалим ее после внедрения list_items_with_count().
'''

# --------------------------------------------------------------------------------------------

# Работа с эндпоинтами GET /items и GET /users/{user_id}/items

'''
Переходим к реализации эндпоинтов, начнем с GET /items. 
В файле app/routes/items.py сначала поправим импорты:
- добавим функцию Query() для работы с query-параметрами
- добавим модель ItemsOut
- добавим функцию list_items_with_count()
Итоговый вид импортов:
'''

# app/routes/items.py

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.database import SessionDep
from app.models.items import ItemOut, ItemUpdate, ItemsOut
from app.repositories.items import get_item, delete_item, patch_item, list_items_with_count
from app.repositories.users import get_user

'''
Теперь реализуем сам эндпоинт GET /items в виде функции read_items().
Не забудем, что user_id нужно передавать со значением None:
'''

@router.get('/', response_model=ItemsOut)
async def read_items(
    session: SessionDep,
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

'''
С эндпоинтом GET /items разобрались, теперь идем в файл app/routes/users.py для
обновления эндпоинта GET /users/{user_id}/items. Для начала актуализируем импорты:
- добавим модель ItemsOut
- заменим импорт list_items_by_user_id() на list_items_with_count(), при этом можно
удалить list_items_by_user_id() из файла app/repositories/items.py
'''

# app/routes/users.py
...
from app.models.items import ItemCreate, ItemOut, ItemsOut
from app.repositories.items import create_item as create_item_repository, list_items_with_count

'''
Теперь перейдем к уже существующей функции get_user_items() и актуализируем ее.
Не забудем, что здесь уже нужно передавать user_id:
'''

@router.get('/{user_id}/items', response_model=ItemsOut)
async def get_user_items(
    user_id: UUID,
    session: SessionDep,
    q: str | None = Query(default=None, description='Поиск по названию'),
    limit: int = Query(default=20, ge=1, le=100, description='Количество записей на странице'),
    offset: int = Query(default=0, ge=0, description='Сколько записей пропустить') 
):
    user = await get_user(session=session, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    
    items, count = await list_items_with_count(
        session=session,
        q=q,
        limit=limit,
        offset=offset,
        user_id=user_id
    )

    return ItemsOut(data=items, count=count)

'''
Все готово, теперь можем тестировать наши эндпоинты!
'''