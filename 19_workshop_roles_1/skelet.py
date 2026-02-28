# Проект воркшопа. Безопасность и авторизация 1

# Введение

'''
На предыдещем занятии мы внедрили в наш проект OAuth2 scopes и научились
закрывать эндпоинты по правам доступа. Важно понимать, что использование
scopes отвечает на вопрос: "Может ли пользователь обращаться к этому эндпоинту?".
Поэтому сегодня мы добавим улучшение нашей системы - объектную авторизацию,
которая отвечат на вопрос: "Может ли пользователь обращаться именно к этому
ресурсу в рамках конкретного эндпоинта?". Например, может ли пользователь
Dima123 получить данные про item "Телефон"? Если это его item или Дима
является админом - доступ есть, иначе - доступ закрыт. К такой логике мы и будем стремиться.

Сегодня мы сосредоточимся именно на работе с items, а уже на следующем занятии поработаем 
с users. В контексте items мы сделаем так, чтобы права владения и доступа соблюдались
автоматически и без переписывания каждого эндпоинта. Для этого сегодня мы добавим в проект:
- Контекст авторизации на запрос
- Сервисный слой для принудительного применения правила "own/any"
'''

# ------------------------------------------------------------------------------------------

# Добавление scopes у роли admin

'''
Преждем, чем мы будем внедрять объектную авторизацию, подправим несколько моментов в текущем
коде проекта. Начнем со scopes для роли admin. Сейчас в декораторах эндпоинтов внутри app/routes/items.py
стоят scopes с ":own" на конце. Кажется, что "админ круче", у него scopes вида ":any", значит
он точно должен иметь доступ к этим эндпоинтам. Но дело в том, что FastAPI при получении токена 
проверят наличие каждого scope, который перечислен в декораторе. А items:read:any не является синонимом
для items:read:own, это просто другая строка. Поэтому если у админа в токене только items:read:any,
а эндпоинт требует items:read:own, то при обращении к эндпоинту получим сообщение "Not enough permissions".

Это очень популярная ошибка при изучении scopes и в нашем проекте мы исправим ее так, что сделаем
админа супермножеством прав. То есть admin будет хранить и ":any", и ":own" scopes, ведь, по сути,
":own" - это частный случай ":any". Конечно, есть и другие способы решить эту ситуацию, но нас устроит
и такой вариант. Для этого откроем файл app/core/security.py и внутри словаря ROLE_TO_SCOPES добавим
scopes с ":own" на конце:
'''

# app/core/security.py

ROLE_TO_SCOPES: dict[str, set[str]] = {
    "user": {
        "items:read:own",
        "items:write:own",
        "users:read:own",
        "users:write:own"
    },
    "admin": {
        "items:read:own",
        "items:write:own",
        "users:read:own",
        "users:write:own",

        "items:read:any",
        "items:write:any",
        "users:read:any",
        "users:write:any"
    }
}

'''
Теперь если мы запустим приложение и залогинемся под admin-ом, то items-эндпоинты нам будут
тоже доступны.
'''

# ------------------------------------------------------------------------------------------

# Добавление роли user при регистрации нового пользователя

'''
Еще один важный момент - регистрация нового пользователя. Когда мы внедрили роли в наш проект,
то допустили еще одну типичную ошибку - не обновили механизм регистрации новых пользователей.
Теперь, по идее, новым пользователям должна по умолчанию присваиваться хоть какая-то роль,
иначе они не смогут воспользоваться ни одним эндпоинтом. Сделаем так, что при регистрации
новым пользователям будет выдавать роль "user". Для этого пойдем даже не в код эндпоинта,
а в код репизитория, то есть app/repositories/users.py. В начале добавим импорты моделей с ролями:
'''

# app/repositories/users.py
...
from app.models.roles import Role, RoleName, UserRoleLink
...

'''
Затем пойдем в функцию create_user() и добавим код по назначению роли "user":
1) Сначала найдем ID роли user в таблице roles
2) Потом создадим связь между новым пользователем и ролью user в таблице user_roles
'''

async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    ...
    stmt_role = select(Role).where(Role.name == RoleName.USER.value)
    role_user = (await session.exec(stmt_role)).first()
    session.add(UserRoleLink(user_id=new_user.id, role_id=role_user.id))

'''
Все готово, теперь у новых пользователей всегда по умолчанию будет роль user.
'''

# ------------------------------------------------------------------------------------------

# Добавление класса AccessUser

'''
Как мы обсуждали ранее, scopes уже проверяются на уровне эндпоинта через конструкцию 
Security(get_current_user, scopes=[...]). Это решает вопрос: 
"Можно ли в принципе использовать эндпоинт?"
Но scopes не решают задачу автоматически задачу объектного доступа: 
"Можно ли этому пользователю читать/менять именно этот item?"
Также нам нужно одинаково применять правило "own или any" во всех местах, не переписывая
код под каждый scope.

Поэтому мы создадим специальный класс-обертку AccessUser, задача которого:
- хранить user (ORM-модель из БД)
- хранить scopes (из JWT-токена)
- делать проверку наличия "own" или "any"

Этот класс поможет нам писать более коротки код внутри будущего сервисного слоя,
не создавая при этом кучу условных конструкций в эндпоинтах.

Итак, создадим файл app/access.py для будущего класса AccessUser.
Пропишем импорты, учитывая следующие моменты:
1) Класс AccessUser мы создадим как dataclass, т.к. AccessUser является небольшим контейнером
данных с одним методом для работы с "own" и "any"
2) Для проверки "own" и "any" внутри метода нам понабится работы с id, а у нас это UUID
3) user - экземпляр класса User, этот класс нам также понадобится для работы
'''

# app/access.py

from dataclasses import dataclass
from uuid import UUID

from app.models.users import User

'''
Далее объявим заголовок дата-класса AccessUser с атрибутами user и scopes.
Учтем при этом следующее:
1) Для атрибута user укажем тип User соответственно
2) Для атрибута scopes укажем тип list[str]
'''

@dataclass(frozen=True, slots=True)
class AccessUser:
    user: User
    scopes: list[str]

'''
Далее внутри класса создадим единственный метод - can(), отвечающий на вопросы:
"Может ли пользователь выполнить действие action над ресурсом resource?
И если ресурс конкретный (например, item), принадлежит ли он пользователю?"

Ранее мы договорились, что в нашей модели scopes последний фрагмент влияет на уровень доступа:
- "any" - доступ ко всем объектам
- "own" - доступ только к объектам, где пользователь является их владельцем

Сигнатура метода сan() будет такой:
'''

...
class AccessUser:
    ...
    def can(self, resource: str, action: str, owner_id: UUID | None = None) -> bool:
        ...

'''
Внутри реализуем метода реализуем 3 сценария:
- Если в scopes пользователя есть scope для доступа к resource и действием action,
а в конце стоит any - возвращаем True, т.к. такой scope есть у админа
- Если передан owner_id и он совпадает с id текущего пользователя - возвращаем True,
если в scopes пользователя есть scope для доступа к resource и действием action,
а в конце стоит own. В противном случае возвращаем False, т.к. scope не нашелся.
- Во всех остальных случаях возвращаем False
Мы как бы по конструктору собираем scope через f-строку и проверяем ее наличие в scopes:
'''

...
class AccessUser:
    ...
    def can(self, resource: str, action: str, owner_id: UUID | None = None) -> bool:
        if f"{resource}:{action}:any" in self.scopes:
            return True
        if owner_id is not None and owner_id == self.user.id:
            return f"{resource}:{action}:own" in self.scopes
        return False

'''
Класс готов. Еще раз закрепим, что AccessUser - это ORM-модель, а вспомогательная обертка,
объект которой живет во время обработки запроса к эндпоинту. С помощью этого класса
проверка для "any или own" не размажется по всему коду.

Осталось внедрить AccessUser в нашу зависимость get_current_user().
Для этого откроем app/deps.py и добавим импорт:
'''

# app/deps.py
...
from app.access import AccessUser
...

'''
Затем для функции get_current_user() поменяем следующее:
- Вместо возвращаемого типа User укажем AccessUser
- В конце, вместо return user укажем return AccessUser(user=user, scopes=token_scopes)
'''

async def get_current_user(
    ...
) -> AccessUser:
    ...
    return AccessUser(user=user, scopes=token_scopes)

'''
Помним, что сами scopes живут внутри JWT-токена. Мы их распарсили и присоединили
к пользователю в AccessUser. Теперь у нас есть единый объект, который удобно
передавать в будущий сервисный слой.
'''

# ------------------------------------------------------------------------------------------

# Внедрение обновленной зависимости get_current_user() в эндпоинты приложения

'''
Мы обновили зависимость get_current_user(), теперь она возвращает объект AccessUser,
состоящий из user и scopes. Настало время обновить сигнатуры наших эндпоинтов 
и внедрить использование зависимости get_current_user() для защиты доступа.

Важно - сейчас мы будем защищать эндпоинты именно через scopes, а значит нам важно следующее:
- Эндпоинт требует scope
- Токен проверяется через get_current_user()
- Swagger начинает показывать требования прав на эндпоинтах

Чтобы внедрить get_current_user() с проверкой scopes, мы воспользуемся новой функцией - Security().
C помощью нее можно создавать зависимости, как и через Depends(), но с той лишь разницей,
что Security() может объявлять scopes по стандарту OAuth2. Начнем с файла app/routes/items.py,
где сначала импортируем:
- класс Annotated для удобного внедрения зависимостей, как это рекомендует создатель FastAPI
- функцию Security()
- функцию get_current_user()
- созданный ранее AccessUser
'''

# app/routes/items.py

from typing import Annotated

from fastapi import Security

from app.deps import get_current_user
...
from app.access import AccessUser
...

'''
Далее для каждой функции добавим новый аргумент - current_user, используя только что импортированные инструменты.

СОВЕТ ПРЕПОДАВАТЕЛЮ: для ускорения можно просто копировать и вставлять строчку
current_user: Annotated[AccessUser, Security(get_current_user, scopes=[...])], вписывая нужный scope.
'''

async def read_items(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:own"])],
):
    ...

          
async def read_item_by_id(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:own"])],
):
    ...

            
async def patch_item_by_id(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:own"])],
):
    ...


async def delete_item_by_id(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:own"])],
):
    ...

'''
Далее мы сделаем то же самое, но уже внутри файла app/routes/users.py и с некоторыми уточнениями:
- create_user() оставим открытой, т.к. это регистрация новых пользоваталей
- остальные эндпоинты пока сделаем админскими, дальше мы модифицируем этот момент
'''

# app/routes/users.py

from typing import Annotated

from fastapi import Security

from app.deps import get_current_user
...
from app.access import AccessUser
...


async def create_user_item(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:write:any"])],
):
    ...


async def read_users(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["users:read:any"])],
):
    ...


async def get_user_by_id(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["users:read:any"])],
):
    ...


async def get_user_items(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["items:read:any"])],
):
    ...
    

async def patch_user(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["users:write:any"])],
):
    ...


async def delete_user_by_id(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["users:write:any"])],
):
    ...

'''
Зависимость get_current_user() успешно интегрирована в эндпоинты, осталось поправить один
маленький момент. В файле app/routes/login.py есть функция test_token(), где используется
зависимость CurrentUser. Нам ее нужно заменить, т.к. раньше get_current_user() возвращала просто User,
и можно было вернуть его напрямую. Теперь же AccessUser, поэтому внесем правки:
- вместо CurrentUser укажем Annotated[AccessUser, Security(get_current_user, scopes=[])].
Обратите внимание, что scopes нет, так мы показываем, что доступ есть у всех авторизованных пользователей.
- вместо return current_user сделаем return current_user.user
'''

# app/routes/login.py

...
from fastapi import Security
...
from app.deps import get_current_user
from app.access import AccessUser
...


@router.post("/test-token", response_model=UserOut)
async def test_token(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=[])]
):
    return current_user.user

'''
Получаем, что зависимость CurrentUser нам больше не нужна, можем удалить ее из файла app/deps.py.

СОВЕТ ПРЕПОДАВАТЕЛЮ: убедитесь, что студенты удалили CurrentUser из файла app/deps.py.
'''