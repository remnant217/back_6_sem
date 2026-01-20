# SQLModel и межтабличные связи

# Создание моделей для сущности Item

'''
Для начала - создадим файл items.py внутри папки app/models/.

В начале пропишем те же импорты, что в app/models/users.py:
'''

# app/models/items.py

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

'''
Далее создадим базовую модель ItemBase, где будут храниться общие поля - title
и description. При этом description может быть необязательным.
'''

class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)

'''
Следующая модель - создание объекта, то есть ItemCreate. Как и в случае с User,
мы просто наследуется от базовой модели ItemBase, без добавления новых полей:
'''

class ItemCreate(SQLModel):
    pass

'''
Далее создадим модели для возвращение ответа клиенту. Сначала опишем ItemOut,
где будем наследоваться от ItemBase, при этом указывая id и user_id, чтобы
клиент видел, кому принадлежит item. 
'''

class ItemOut(ItemBase):
    id: UUID
    user_id: UUID

'''
И сразу же создадим модель ItemsOut в стиле UsersOut - для возвращения
списка объектов:
'''

class ItemsOut(SQLModel):
    data: list[ItemOut]
    count: int

'''
Также добавим модель для обновления объекта - ItemUpdate, где клиенту
можно поменять title и description. Все поля, соответственно, опциональны.
'''

class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=128)

'''
Нам осталось реализовать класс Item - непосредственно объект таблицы внутри БД.
Структура будет такая же, как для класса User, только добавится поле user_id,
выступающее в роли внешнего ключа.
'''

class Item(ItemBase, table=True):
    __tablename__ = 'items'
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key='users.id',     # внешний ключ - поле id из таблицы users
        nullable=False              # Item не может существовать без User, поэтому поле обязательное       
    )

# --------------------------------------------------------------------------------------------------------------

# Миграция items через Alembic

'''
Итак, мы создали связь между User и Item на уровне Python-кода, но этой связи еще нет на уровне базы данных,
как и самой таблицы items. Чтобы применить изменения к БД, воспользуемся Alembic. Для этого в файл alembic/env.py
добавим импорт созданного ранее модуля items:
'''

# alembic/env.py
...
from app.models import items
...

'''
Теперь сгенерируем новую миграцию. Для этого выполним в терминале следующую команду:

В терминале:
alembic revision --autogenerate -m "create items table"

В папке alembic/versions появился файл ..._create_items_table.py. Давайте посмотрим внимательно
на код внутри него. В начале файла мы видим следующие импорты:
'''

# ..._create_items_table.py

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

'''
А ниже мы видим следующие строчки:
'''

sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),

'''
Видим проблему - в файле на импортирован модуль sqlmodel.sql.sqltypes, поэтому среда разработки
и показывает соответствующее предупреждение. Если мы попробуем применить эту миграцию, то увидим ошибку про
отсутствие импорта sqlmodel. Как вариант - можно в данном файле миграции указать import sqlmodel.sql.sqltypes
и тогда миграция сработает. Но так нужно будет делать для каждой следующей миграции, что, согласитесь, не очень
удобно. Получается, нужно настроить Alembic так, чтобы в начале каждого нового файла миграции была строчка
import sqlmodel.sql.sqltypes. И в этом нам поможет файл alembic/script.py.mako, который позволяет контролировать
структуру каждого файла миграции. Откроем этот файл и добавим к остальным импортам нужную нам конструкцию:
'''

# alembic/script.py.mako

# добавляем рядом с остальными импортами
import sqlmodel.sql.sqltypes

'''
Готово, теперь все будущие миграции будут содержать в начале строку import sqlmodel.sql.sqltypes.
Удалим текущий файл миграции ..._create_items_table.py и создадим новый с помощью той же команды в терминале:

В терминале:
alembic revision --autogenerate -m "create items table"

Попробуем применить данную миграцию:

В терминале:
alembic upgrade head

Миграция успешно применилась. 
'''

# --------------------------------------------------------------------------------------------------------------

# Реализация слоя репозитория для items

'''
Для начала создадим файл items.py в папке app/repositories.
В начале укажем необходимые импорты, похожие на репозиторий users.py:
'''

# app/repositories/items.py
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.items import Item, ItemCreate

'''
Далее реализуем функцию create_item() для создания объекта с привязкой
к конкретному пользователю по его user_id:
'''

async def create_item(session: AsyncSession, user_id: UUID, item_data: ItemCreate) -> Item:
    new_item = Item(**item_data.model_dump(), user_id=user_id)
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return new_item

'''
Затем реализуем функцию get_item() для получения объекта по первичному ключу, то есть ID:
'''

async def get_item(session: AsyncSession, item_id: UUID) -> Item | None:
    return await session.get(Item, item_id)

'''
Осталось реализовать функцию для получения объектов, принадлежащих конкретному пользователю.
Связь один-ко-многим реализована у нас через внешний ключ Item.user_id.
Поэтому, чтобы получить items пользователя, будем сравнивать полученный извне user_id
с Item.user_id: 
'''

async def list_items_by_user_id(session: AsyncSession, user_id: UUID) -> list[Item]:
    stmt = select(Item).where(user_id == Item.user_id)
    result = await session.exec(stmt)
    return result.all()

# --------------------------------------------------------------------------------------------------------------

# Реализация эндпоинтов для работы с items

'''
Нам осталось реализовать несколько базовых эндпоинтов для одновременной работы с пользователями
и принадлежащими их объектами. Начнем с того, что создадим файл items.py в папке app/routes.
Внутри app/routes/items.py реализуем эндпоинт для получения объекта по его ID.
Укажем все необходимые импорты, объявим роутер и ниже создадим описанный ранее эндпоинт.
'''

# app/routes/items.py

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.models.items import ItemOut
from app.repositories.items import get_item

router = APIRouter(prefix='/items', tags=['items'])

@router.get('/{item_id}', response_model=ItemOut)
async def read_item_by_id(item_id: UUID, session: SessionDep):
    item = await get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    return item

'''
Остальные эндпоинты мы реализуем уже внутри файла app/routes/users.py, т.к. это будут
эндпоинты "подресурса" - они будут описывать действия над items для конкретного пользователя.
То есть главным ресурсом будет User, а items будут вложенной коллекцией, с которой мы связываемся
через внешний ключ user_id. Конечно, это не единственный способ для решения нашей задачи,
но на данный момент - наиболее удобный.

Для начала добавим необходимые импорты в файл app/routes/users.py:
'''

# app/routes/users.py

from app.models.items import ItemCreate, ItemOut
from app.repositories.items import create_item as create_item_repository, list_items_by_user_id

'''
Затем в конце файла добавим два новых эндпоинта:
1) POST /users/{user_id}/items - создаем новый item для конкретного пользователя
2) GET /users/{user_id}/items - получаем список items для конкретного пользователя
'''

@router.post('/{user_id}/items')
async def create_user_item(user_id: UUID, item_data: ItemCreate, session: SessionDep):
    user = await get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    new_item = await create_item_repository(session=session, user_id=user_id, item_data=item_data)
    return new_item

@router.get('/{user_id}/items')
async def get_user_items(user_id: UUID, session: SessionDep):
    user = await get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    items_list = await list_items_by_user_id(session=session, user_id=user_id)
    return items_list

'''
Эндпоинты готовы, осталось подключить новый роутер в app/main.py:
'''

# app/main.py

from app.routes.items import router as items_router
...
app.include_router(items_router)

'''
Весь код готов! Запустим наше приложение и попробуем создать объекты для конкретных пользователей.
'''