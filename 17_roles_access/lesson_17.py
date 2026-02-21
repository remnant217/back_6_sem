# Роли и доступы

# Реализация ролей в коде

'''
Начнем с создания файла app/models/roles.py. Внутри создадим 2 класса для описания таблиц в БД:
- Role - класс таблицы roles, хранит информацию о ролях
- UserRoleLink - класс таблицы user_roles, таблица связей между roles и users

Пропишем необходимые импорты и базовые заготовки классов:
'''

# app/models/roles.py

from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.users import User


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_roles"


class Role(SQLModel, table=True):
    __tablename__ = "roles"

'''
Дополним код класса UserRoleLink. Важный момент - у таблицы user_roles будет составной первичный ключ,
(user_id, role_id), чтобы одна и та же роль не назначалась одному и тому же пользователю дважды.
'''

...
class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: UUID = Field(
        foreign_key="users.id",
        primary_key=True,
        ondelete="CASCADE"
    )
    role_id: UUID = Field(
        foreign_key="roles.id",
        primary_key=True,
        ondelete="CASCADE"
    )
...

'''
Перед тем, как пойдем дописывать класс Role, сверху создадим дополнительный класс RoleName,
который будет наследоваться от StrEnum. Внутри мы укажем роли для пользователей - USER и ADMIN.
При желании в дальнейшем этот класс можно будет расширить другими ролями. Так у нас будет
один источник о ролях внутри кода.
'''

from enum import StrEnum
...
class RoleName(StrEnum):
    USER = "user"
    ADMIN = "admin"
...

'''
Вот теперь переходим к доработке класса Role. Несколько важных моментов:

1) Поле name с названием роли для простоты сделаем строкой, но значения будем брать из RoleName. 
Также для name укажем unique=True для гарантии, что названия ролей не будут повторяться. 

2) Для окончательной реализации связи "многие-ко-многим" создадим поле users - список с объектами User. 
При использовании функции Relationship() внутри укажем 2 важных параметра:
- back_populates="roles" - связываем это поле с моделью User, чтобы ORM корректно синхронизировала
обе стороны отношения
- link_model=UserRoleLink - показываем, что связь "многие-ко-многим" реализована через таблицу user_roles
'''

...
class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(
        default=RoleName.USER.value,
        unique=True,
        min_length=2,
        max_length=32
    )
    description: str | None = Field(default=None, max_length=200)
    users: list["User"] = Relationship(
        back_populates="roles",
        link_model=UserRoleLink
    )

'''
Супер, с файлом app/models/roles.py разобрались, теперь нужно отредактировать
файл app/models/users.py, чтобы у пользователя появился список его ролей.

Изменения в файле app/models/users.py:
- Добавляем импорты классов Role и UserRoleLink. Обратите внимание, что импорт класса Role
безопасен, т.к. в app/models/roles.py нет импорта класса User в рантайме, только при TYPE_CHECKING.
- Добавляем поле roles в модель User. Т.к. мы импортировали класс User, 
то при указания типа поля roles мы будем его использовать напрямую (list[Role]), без строк (list["Role"]).
'''

# app/models/users.py

...
from app.models.roles import Role, UserRoleLink

...
class User(UserBase, table=True):
    ...
    roles: list[Role] = Relationship(
        back_populates="users",
        link_model=UserRoleLink
    )

# ------------------------------------------------------------------------------------------------

# Применение Alembic-миграции

'''
Чтобы новые таблицы появились в БД, необходимо создать и выполнить Alembic-миграцию.

Открываем alembic/env.py и добавляем импорт roles рядом с текущими импортами:
'''

# alembic/env.py

...
from app.models import roles

'''
Теперь создаем новую миграцию:

В терминале:

alembic revision --autogenerate -m "create roles tables"

В папке alembic/versions появится файл ..._create_roles_tables.py.

Применим созданную миграцию:

В терминале:

alembic upgrade head

Миграция выполнена успешно! Если мы откроем DBeaver, то увидим 2 новые таблицы - roles и user_roles.
'''

# ------------------------------------------------------------------------------------

# Написание скрипта для создания ролей и первого админа

'''
Итак, у нас готовы таблицы roles и user_roles, но пока что они пустые.
Сейчас мы будем это исправлять - создадим роли user и admin, 
а также первого пользователя-админа внутри нашей БД.
Важно - данные первого пользователя-админа будем хранить отдельно,
в .env-файле. Поэтому сперва пойдем в .env-файл и добавим данные для первого админа:
'''

# .env

FIRST_ADMIN_USERNAME=admin
FIRST_ADMIN_PASSWORD=Admin12345678

'''
Соответственно, в файле app/core/config.py, внутри класса Settings, добавим новые поля:
'''

# app/core/config.py

class Settings(BaseSettings):
    ...
    FIRST_ADMIN_USERNAME: str
    FIRST_ADMIN_PASSWORD: str

'''
Так мы не будем хранить username и password явно в коде - они задаются окружением,
что является плюсом к универсальности и безопасности.

Следующий шаг - реализовать само добавление ролей и первого админа в БД.
Важный момент - сделаем мы это через отдельный Python-скрипт.
Скрипт получится немаленький, хотя кажется, что нам нужно сделать не так много вещей - 
добавить 1 пользователя, 2 роли и 1 связь между пользователем и ролью.
Плюс в том, что его достаточно запустить один раз, чтобы в БД появились роли и первый админ.
Также данный скрипт должен быть идемподентным - если его запустить повторно,
то роли не должны сбиваться и первый админ не должен создаваться заново.

Для скрипта создадим отдельный файл app/core/init_roles.py.

Начнем написание скрипта с объявления функции, внутри которой будет все
происходить - create_roles_and_admin(). Т.к. у нас весь стек асинхронный, то и 
функция тоже будет асинхронная. Первым делом проверим, указаны ли FIRST_ADMIN_USERNAME 
и FIRST_ADMIN_PASSWORD в .env-файле. Если нет - вызовем специальное исключение 
SystemExit() для завершения скрипта с пояснением, что одно из значений не указано в файле:
'''

# app/core/init_roles.py

from app.core.config import settings


async def create_roles_and_admin():
    if not settings.FIRST_ADMIN_USERNAME or not settings.FIRST_ADMIN_PASSWORD:
        raise SystemExit("FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD are not set in .env")
    
'''
Далее мы пропишем логику создания ролей внутри таблицы roles, если их еще там.
Логика будет следующая:
1) Открываем сессию для работы с БД
2) Пробуем выгрузить все роли из таблицы roles в виде последовательности объектов класса Role.
3) Собираем множество из всех названий ролей, чтобы быстро проверять наличие роли по имени.
4) Проверяем наличие ролей "user" и "admin" в БД (в созданном множестве) - если роли нет,
то добавляем новую роль в текущую сессию.
5) Сохраняем изменения в БД - если мы добавили роли, то они реально создадутся в таблице roles.
'''

from sqlmodel import select
...
from app.database import AsyncSessionLocal
from app.models.roles import Role, RoleName
...

async def create_roles_and_admin():
    ...
    async with AsyncSessionLocal() as session:
        roles = (await session.exec(select(Role))).all()
        roles_by_name = {r.name for r in roles}

        if RoleName.USER.value not in roles_by_name:
            session.add(
                Role(name=RoleName.USER.value, description="Default user role")
            )
        if RoleName.ADMIN.value not in roles_by_name:
            session.add(
                Role(name=RoleName.ADMIN.value, description="Admin role")
            ) 

        await session.commit()

'''
Готово, теперь мы точно уверены, что необходимые роли есть в БД.
Теперь отдельно выгрузим объект с ролью админа, чтобы знать ее id в БД.
Нам это понадобится при создании самого админа:
'''

async def create_roles_and_admin():
    ...
        role_admin = (
            await session.exec(select(Role).where(Role.name == RoleName.ADMIN.value))
        ).one()

'''
Следующий шаг - создать первого админа, если его еще нет в БД.
Алгоритм будет следующий:
1) Выгрузить из таблицы users пользователя, чей username совпадает с 
FIRST_ADMIN_USERNAME.
2) Если такого пользователя нет в БД - создаем нового пользователя
с username равным FIRST_ADMIN_USERNAME и password равным FIRST_ADMIN_PASSWORD.
3) Сохраняем нового пользователя внутри БД.
'''

...
from app.models.users import User, UserCreate
from app.repositories.users import create_user
...

async def create_roles_and_admin():
    ...
        admin_user = (
            await session.exec(
                select(User).where(User.username == settings.FIRST_ADMIN_USERNAME)
            )
        ).first()

        if admin_user is None:
            admin_in = UserCreate(
                username=settings.FIRST_ADMIN_USERNAME,
                password=settings.FIRST_ADMIN_PASSWORD
            )
            admin_user = await create_user(session=session, user_data=admin_in)

'''
Осталось финальное действие в нашей функции - назначить созданному пользователю роль админа.
Алгоритм будет следующий:
1) Проверяем наличие связи для admin_user и role_admin в таблице user_roles.
2) Если связи нет - создаем связь, делая admin_user действительно админом
3) Сохраняем изменения в БД 
'''

...
from app.models.roles import UserRoleLink


async def create_roles_and_admin():
    ...
        link = (await session.exec(
            select(UserRoleLink).where(
                (UserRoleLink.user_id == admin_user.id) &
                (UserRoleLink.role_id == role_admin.id)
            )
        )).first()

        if link is None:
            session.add(UserRoleLink(user_id=admin_user.id, role_id=role_admin.id))
            await session.commit()

'''
Наша функция готова, осталось убедиться, что она будет работать только как скрипт.
Для этого внизу укажем конструкцию if __name__ == "__main__": и внутри
асинхронного вызовем create_roles_and_admin().
'''

import asyncio
...

if __name__ == "__main__":
    asyncio.run(create_roles_and_admin())

'''
Скрипт готов! Попробуем его запустить через следующую команду:

В терминале:
python -m app.core.init_roles

И у нас появится следующая ошибка:
sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[User(users)], 
expression 'Item' failed to locate a name ('Item'). 
If this is a class name, consider adding this relationship() to the <class 'app.models.users.User'> 
class after both dependent classes have been defined.

Дело в том, что наш скрипт импортирует модель User, но не импортирует модель Item, а в модели User есть поле:

items: list["Item"] = Relationship(...)

Когда происходит первое выполнение session.exec(select(Role)), SQLModel видит у User связь с "Item"
и пытается найти класс Item в реестре моделей. Но модуль app.models.items не был импортирован, 
поэтому класс Item не зарегистрирован, в результате и получаем: "expression 'Item' failed to locate a name ('Item')"

Самый простой вариант исправления - добавить в начало скрипта импорт моделей items.
Он нужен только для регистрации класса:
'''

# app/core/init_roles.py

...
from app.models import items
...

'''
Повторно запустим скрипт:

В терминале:
python -m app.core.init_roles

Теперь все пройдет успешно, это можно увидеть по логам работы sqlalchemy в терминале.
Если мы сейчас откроем DBeaver, то увидим:
- В таблице users появился пользователь admin
- В таблице roles появились 2 роли - user и admin
- В таблице user_roles появилась связь между ролью admin и пользователем admin

Все получилось! На следующем занятии мы продолжим работу с ролями и разграничением доступа.
'''