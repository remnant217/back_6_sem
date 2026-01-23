# SQLModel и углубленная работа с транзакциями

# Функция Relationship() и циклические импорты

'''
Начнем внедрять Relationship Attributes в код наших моделей User и Item.

Сначала пойдем, например, в app/models/users.py и импортируем функцию Relationship()
из модуля SQLModel. Именно с помощью Relationship() мы сможем объявлять Relationship Attributes.
'''

# app/models/users.py

from sqlmodel import Field, SQLModel, Relationship
...

'''
Затем в классе User добавим новый атрибут items, обозначающий список объектов
Item для конкретного пользователя. Именно тут нам и пригодится функция Relationship():
'''

class User(UserBase, table=True):
    ...
    items: list["Item"] = Relationship(back_populates="user")

'''
Пока что с app/models/users.py разобрались, теперь пойдем и реализуем то же самое, но в
app/models/items.py:
'''

# app/models/items.py

from sqlmodel import Field, SQLModel, Relationship
...
class Item(ItemBase, table=True):
    ...
    user: User = Relationship(back_populates="items")

'''
С Relationship() разобрались, но есть некоторые проблемы в текущем коде.
В app/models/users.py мы обращаемся к классу Item, которого нет в этом модуле.
И также в app/models/items.py мы обращаемся к классу User, которого тоже нет в этом модуле.

Вроде бы, чтобы решить проблему, нам нужно в модуль items импортировать класс User,
а в users - класс Item. Попробуем так и сделать - добавим нужные импорты:
'''

# app/models/users.py

from app.models.items import Item
...

# app/models/items.py

from app.models.users import User
...

'''
Если мы сейчас попробуем запустить приложение, то увидим следующую ошибку:
ImportError: cannot import name 'User' from partially initialized module 'app.models.users'

А это ни что иное, как циклический импорт.

В официальной документации по SQLModel предлагается следующее решение данной проблемы.
Можно воспользоваться специальной переменной TYPE_CHECKING из встроенного модуля typing.
Рассмотрим на примере app/models/users.py. Сначала подключим эту переменную в коде:
'''

# app/models/users.py

from typing import TYPE_CHECKING
...

'''
Затем ниже укажем условие - если значение переменной TYPE_CHECKING равно True, то мы
выполняем from app.models.items import Item:
'''

if TYPE_CHECKING:
    from app.models.items import Item

'''
Проделаем то же самое для app/models/items.py: 
'''

# app/models/items.py

from typing import TYPE_CHECKING
...
if TYPE_CHECKING:
    from app.models.users import User

'''
Только есть одно важное дополнение для app/models/items.py. В строчке с объявлением атрибута user внутри 
класса Item, класс User нужно обязательно взять в кавычки, иначе будет ошибка:
'''

class Item(ItemBase, table=True):
    ...
    user: "User" = ...


# --------------------------------------------------------------------------------

# Обновление репозитория и эндпоинтов

'''
Ранее мы добавили в наши ORM-модели работу с функцией Relationship(), теперь применим
это для репозитория и эндпоинтов. Начнем с эндпоинта POST /users/{user_id}/items, где мы 
создаем item для указанного пользователя. Наша задача - внедрить в него использования
объектного подхода, доступного с помощью внедренного ранее Relationship().

Для начала обратимся к репозиторию, а именно к файлу app/repositories/items.py.
'''

# app/repositories/items.py

from app.models.users import User
...

'''
Затем в самой функции сделаем следующие корректировки:
1) В заголовке функции, параметр user_id: UUID заменим на user: User.
2) При создании экземпляра класса Item вместо user_id=user_id укажем user=user.
'''

async def create_item(session: AsyncSession, user: User, item_data: ItemCreate):
    new_item = Item(**item_data.model_dump(), user=user)
    ...

'''
Репозиторий обновлен, теперь пойдем к обновлению самого эндпоинта POST /users/{user_id}/items.
'''

# app/routes/users.py

...
new_item = await create_item_repository(session=session, user=user, item_data=item_data)
...

'''
Двигаемся дальше и попробуем создать новый эндпоинт, задача которого - обновить существущий item и, 
в частности, перенести item другому пользователю. 
Начнем реализацию данного эндпоинта с модели обновления Item, а именно - ItemUpdate.
Сейчас через данную модель можно передать только title и description.
Чтобы можно было сменить владельца, добавим опциональное поле user_id:
'''

# app/models/users.py

class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    user_id: UUID | None = None

'''
С моделью разобрались, переходим к слою репозитория. Т.к. здесь главной сущностью является именно item,
то и функцию репозиторного слоя будем размещать в app/repositories/items.py.

СОВЕТ ПРЕПОДАВАТЕЛЮ: на предыдущем занятии у студентов было ДЗ по добавлению возможности удаления
item по ID. Соответствующие функции должны быть в файлах app/repositories/items.py и app/routes/items.py.
Если на занятии останется время, то в конце занятия реализуйте эти функции, чтобы у всех студентов
удаление item было в проектах. Если времени не хватает, то реализуйте эти функции в начале следующего занятия.
'''

# app/repositories/items.py

from app.models.items import Item, ItemCreate, ItemUpdate
...
async def patch_item(
    session: AsyncSession,
    item_db: Item,
    item_data: ItemUpdate,
    new_user: User | None = None
) -> Item:
    # обновляем связь через Relationship(), если передан новый владелец
    if new_user is not None:
        item_db.user = new_user
    # обновляем остальные поля, кроме user_id
    data = item_data.model_dump(exclude_unset=True, exclude={'user_id'})
    item_db.sqlmodel_update(data)

    session.add(item_db)
    await session.commit()
    await session.refresh(item_db)
    return item_db

'''
Со слоем репозитория разобрались, теперь идем реализовывать эндпоинт в файле app/routes/items.py.
Внутри предусмотрим следующие крайние случаи:
- Если item с указанным ID не найден, то возвращаем статус 404 с сообщением 'Item not found'
- Если клиент в JSON для user_id передал null, то возвращаем статус 422 с сообщением 'user_id cannot be null'
- Если user с указанным ID не найден, то возвращаем статус 404 с сообщением 'User not found'
Не забудем также подключить созданную ранее функцию patch_item() и модель ItemUpdate.
А т.к. нам нужно будет еще проверять наличие пользователя с указанным ID, то подключим еще
и функцию get_user().
'''

# app/routes/items.py

from app.models.items import ItemOut, ItemUpdate
from app.repositories.items import get_item, delete_item, patch_item
from app.repositories.users import get_user
...
@router.patch('/{item_id}', response_model=ItemOut)
async def patch_item_by_id(item_id: UUID, item_data: ItemUpdate, session: SessionDep):
    item_db = await get_item(session, item_id)
    if item_db is None:
        raise HTTPException(status_code=404, detail='Item not found')
    
    payload = item_data.model_dump(exclude_unset=True)
    new_user = None

    # если клиент хочет сменить владельца, то он должен явно прислать user_id
    if 'user_id' in payload:
        # запрещаем клиенту отправлять null для user_id
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

'''
Запустим наше приложение и проверим работу нового эндпоинта.
'''