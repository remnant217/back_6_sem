# Проект воркшопа. Безопасность и авторизация 

# Введение

'''
На предыдущем занятии мы внедрили в наш проект OAuth2 scopes как инструмент 
для защиты эндпоинтов по правам доступа. Важно понимать, что использование
scopes отвечает на вопрос: "Может ли пользователь обращаться к этому эндпоинту?".
Поэтому сегодня мы добавим улучшение нашей системы - объектную авторизацию,
которая отвечает на вопрос: "Может ли пользователь обращаться именно к этому
ресурсу в рамках конкретного эндпоинта?". Например, может ли пользователь
Dima123 получить данные про item "Телефон"? Если это его item или Дима
является админом - доступ есть, иначе - доступ закрыт. К такой логике мы и будем стремиться.

В рамках воркшопа мы сначала сосредоточимся на работе с items-эндпоинтами,
а уже затем поработаем с users-эндпоинтами.
В контексте items мы сделаем так, чтобы права владения и доступа соблюдались
автоматически и без переписывания каждого эндпоинта. Для этого сегодня мы добавим в проект:
- Контекст авторизации на запрос
- Сервисный слой для принудительного применения правила "own/any"
'''

# ------------------------------------------------------------------------------------------

# Добавление scopes у роли admin

'''
Прежде, чем мы будем внедрять объектную авторизацию, подправим несколько моментов в текущем коде проекта. 
Начнем со scopes для роли admin. В текущей реализации   кажется, что «админ круче» – у него scopes вида ":any", 
значит он точно должен иметь доступ ко всем эндпоинтам. Но дело в том, что FastAPI при получении токена  
проверят наличие каждого scope, который перечислен в декораторе. А items:read:any, например, 
не является синонимом для items:read:own, это просто другая строка. 
Поэтому если у админа в токене только items:read:any, а эндпоинт требует items:read:own, 
то при обращении к эндпоинту получим сообщение "Not enough permissions".

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

# ------------------------------------------------------------------------------------------

# Добавление роли user при регистрации нового пользователя

'''
Еще один важный момент - регистрация нового пользователя. Когда мы внедрили роли в наш проект,
то допустили еще одну типичную ошибку - не обновили механизм регистрации новых пользователей.
Теперь, по идее, новым пользователям должна по умолчанию присваиваться хоть какая-то роль,
иначе они не смогут воспользоваться ни одним эндпоинтом. Сделаем так, чтобы при регистрации
новым пользователям будет выдаваться роль "user". Для этого пойдем даже не в код эндпоинта,
а в код репозитория, то есть app/repositories/users.py. В начале добавим импорты моделей с ролями:
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
Как мы обсуждали ранее, scopes отвечают на  вопрос: 
"Можно ли в принципе использовать эндпоинт?"
Но scopes не решают автоматически задачу объектного доступа: 
"Можно ли этому пользователю читать/менять именно этот item?"
Также нам нужно одинаково применять правило "own или any" во всех местах, не переписывая
код под каждый scope.

Поэтому мы создадим специальный класс-обертку AccessUser, задача которого:
- хранить user (ORM-модель из БД)
- хранить scopes (из JWT-токена)
- делать проверку наличия "own" или "any"

Этот класс поможет нам писать более короткий код внутри будущего сервисного слоя,
не создавая при этом кучу условных конструкций в эндпоинтах.

Итак, создадим файл app/access.py для будущего класса AccessUser.
Пропишем импорты, учитывая следующие моменты:
1) Класс AccessUser мы создадим как dataclass, т.к. AccessUser является небольшим контейнером
данных с одним методом для работы с "own" и "any"
2) Для проверки "own" и "any" внутри метода нам понадобится работы с id, а у нас это UUID
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
Класс готов. Еще раз закрепим, что AccessUser - это не ORM-модель, а вспомогательная обертка,
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
- созданный ранее класс AccessUser
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

СОВЕТ ПРЕПОДАВАТЕЛЮ: для ускорения процесса можно просто копировать и вставлять строчку
current_user: Annotated[AccessUser, Security(get_current_user, scopes=[...])], вписывая нужный scope.
Можете задействовать студентов, чтобы те говорили, какой именно scope нужно указать для конкретного эндпоинта.
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
- create_user() оставим открытой, т.к. это регистрация новых пользователей
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
и можно было вернуть его напрямую. Теперь возвращается же AccessUser, поэтому внесем правки:
- вместо CurrentUser укажем Annotated[AccessUser, Security(get_current_user, scopes=[])].
Обратите внимание, что scopes - это пустой список, так мы показываем, 
что доступ есть у всех авторизованных пользователей.
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
Получается, что зависимость CurrentUser нам больше не нужна, можем удалить ее из файла app/deps.py.

СОВЕТ ПРЕПОДАВАТЕЛЮ: убедитесь, что студенты удалили CurrentUser из файла app/deps.py.
'''

# -----------------------------------------------------------------------------------------------

# Создание сервисного слоя

'''
Итак, друзья, scopes у нас есть, зависимости внедрены в эндпоинты, а значит защита данных присутствует.
Но доступ к конкретным ресурсам пока еще работает не до конца корректно.
Например, если мы запустим приложение и залогинимся под обычным пользователем (не под админом),
а затем выполним запрос к GET /items/, то получим вообще все items, а не только items текущего
пользователя. То же самое касается и запроса GET /items/{item_id} - если мы знаем UUID item-а,
то без проблем можем получить его, даже если это не наш item. Это неправильно и так быть не должно.

СОВЕТ ПРЕПОДАВАТЕЛЮ: если позволяет время, то запустите приложение и продемонстрируйте
описанные выше проблемы.

Почему так происходит? Потому что в текущей архитектуре наши слои делают следующее:
- routes - функции принимают запросы и вызывают функции ниже 
- repositories - функции выполняют операции с БД

И пока нигде нет места, где по конкретным правилам решается вопрос:
"Может ли этот пользователь выполнять данное действие над данным ресурсом?"

Да, такие проверки можно писать прямо в эндпоинтах, но тогда получится:
- Много дублирующего кода
- Выше вероятность ошибок
- Сложно тестировать и поддерживать

Поэтому мы и вводим в приложении сервисный слой.

Давайте быстро вспомним разницу между репозиторным и сервисным слоями.

СОВЕТ ПРЕПОДАВАТЕЛЮ: если позволяет время, то задействуйте студентов, для них это
не новый материал.

1) Репозиторный слой отвечает за операции над базой данных.
Например:
- Создать новый item
- Выгрузить список активных пользователей
- Обновить item конкретного пользователя
- Удалить пользователя
То есть репозиторный слой отвечает за БД, не за права и доступы.

2) Сервисный слой определяет что можно делать над конкретными ресурсами в соответствии
с заданными правилами.
Например, если есть правило "user может читать только свои items", то при обращении
к чужому item сервис вернет, например, None.

То есть сервис - это бизнес-логика + безопасность на уровне объекта.

Перейдем к созданию файлов и папок сервисного слоя.

Теперь создадим папку app/services, там будут лежать все файлы сервисного слоя.
Внутри папки сразу создадим файлы app/services/items.py и app/services/users.py.
'''

# -----------------------------------------------------------------------------------------------

# Реализация файла app/services/items.py

'''
Итак, начнем с файла app/services/items.py. Давайте сначала договоримся о функциях, которые
будут внутри и пропишем заголовки функций с заглушками, чтобы обозначить общую структуру.
Важная договоренность - сервис должен быть удобен функциям-эндпоинтам, поэтому сейчас опишем 
функции, которые почти 1-в-1 соответствуют нашим текущим репозиторным функциям.

СОВЕТ ПРЕПОДАВАТЕЛЮ: рекомендуется параллельно писать код и рассказывать назначения
для каждой функции.

- get_items_with_count() - вернуть список items и общее количество записей с учетом прав: 
user получает только свои items, admin - все.
- get_item_for_read() - получить item по id, но вернуть None, если доступ запрещен 
(user не должен знать о существовании чужих item).
- get_item_for_write() - получить item по id для изменения/удаления, 
но вернуть None, если нет прав на изменение (user может менять только свои item, admin - любые). 
- patch_item() - обновить поля item (без смены владельца), предполагая, что доступ уже проверен через get_item_for_write().
Для смены владельца сделаем отдельную, админскую функцию. Так будет лучше с точки зрения безопасности.
- delete_item() - удалить item, предполагая, что доступ уже проверен через get_item_for_write().
- change_item_owner() - админская операция: сменить владельца item на другого пользователя (возвращает None,
если item не найден)
'''

# app/services/items.py

async def get_items_with_count():
    '''
    Вернуть список items и общее количество записей с учетом прав: 
    user получает только свои items, admin - все.
    '''


async def get_item_for_read():
    '''
    Получить item по id, но вернуть None, если доступ запрещен
    (user не должен знать о существовании чужих item).
    '''


async def get_item_for_write():
    '''
    Получить item по id для изменения/удаления, 
    но вернуть None, если нет прав на изменение 
    (user может менять только свои item, admin - любые).
    '''


async def patch_item():
    '''
    Обновить поля item (без смены владельца), предполагая, 
    что доступ уже проверен через get_item_for_write().
    '''


async def delete_item():
    '''
    Удалить item, предполагая, что доступ уже проверен через get_item_for_write().
    '''


async def change_item_owner():
    '''
    Админская операция: сменить владельца item на другого пользователя 
    (возвращает None, если item не найден)
    '''


'''
Итак, перейдем к реализации функций, для этого сначала пропишем необходимые импорты:
'''

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.access import AccessUser
from app.models.items import Item, ItemUpdate
from app.repositories import items as items_repo
from app.repositories import users as users_repo


'''
СОВЕТ ПРЕПОДАВАТЕЛЯ: можете в соседнем окне открыть файл репозитория
app/repositories/items.py и отсылаться к нему при реализации
соответствующих функций в сервисном слое.

Перейдем к реализации функции get_items_with_count().
Текущая проблема - user сейчас видит все items, даже чужие.
Решение - сервис сам подставляет user_id, тогда user получается
только свои items, admin - все.
'''

async def get_items_with_count(
    session: AsyncSession,
    current_user: AccessUser,
    q: str | None,
    limit: int,
    offset: int
) -> tuple[list[Item], int]:
    # есть ли "any" в scopes (да - admin, нет - user)
    if current_user.can("items", "read"):
        user_id = None
    else:
        user_id = current_user.user.id
    
    return await items_repo.list_items_with_count(
        session=session,
        q=q,
        user_id=user_id,
        limit=limit,
        offset=offset
    )


'''
Перейдем к следующей функции - get_item_for_read().
Она также будет принимать аргументы session и current_user, но дополнительно
будем передавать item_id.
'''

async def get_item_for_read(
    session: AsyncSession,
    current_user: AccessUser,
    item_id: UUID
) -> Item | None:
    item = await items_repo.get_item(session=session, item_id=item_id)
    if item is None:
        return None
    
    if current_user.can("items", "read", owner_id=item.user_id):
        return item
    
    return None

'''
По такой же логике сделаем функцию get_item_for_write().
Мы делаем две отдельные функции с похожим содержимым, т.к.
права на чтение и запись у нас отличаются. И мы хотим, чтобы эндпоинты
PATCH и DELETE использовали get_item_for_write(), а GET-эндпоинты - версию 
get_item_for_read().
'''

async def get_item_for_write(
    session: AsyncSession,
    current_user: AccessUser,
    item_id: UUID
) -> Item | None:
    item = await items_repo.get_item(session=session, item_id=item_id)
    if item is None:
        return None
    
    if current_user.can("items", "write", owner_id=item.user_id):
        return item
    
    return None

'''
Далее по списку - функция patch_item(), без смены владельца, не забываем про это.
Смена владельца будет в отдельной функции. Эта функция будет вызываться внутри
соответствующего эндпоинта после успешной работы функции get_item_for_write().
'''

async def patch_item(
    session: AsyncSession,
    item_db: Item,
    item_data: ItemUpdate
) -> Item:
    return await items_repo.patch_item(
        session=session,
        item_db=item_db,
        item_data=item_data,
        new_user=None
    )

'''
В такой же логике пропишем функцию delete_item().
'''

async def delete_item(
    session: AsyncSession,
    item_db: Item
) -> None:
    await items_repo.delete_item(session=session, item=item_db)

'''
Может показаться, что в функциях patch_item() и delete_item()
мы просто вызываем такие же репозиторные функции. Зачем же тогда создавать
эти сервисные функции, если они просто оборачивают уже готовый код?
На самом деле этими функциями мы обеспечиваем:
- Общую консистентность и архитектуру кода
- Вся логика остается в сервисе, эндпоинты просто ее используют
- Со временем доп. логика может появиться, и тогда достаточно
дописать сервис, без изменения кода эндпоинтов.

Двигаемся дальше и пропишем финальную сервисную функцию - change_item_owner().
Это отдельная операция, т.к. она потенциально опаснее обычного PATCH-запроса,
поэтому мы сделаем ее админской. На уровне эндпоинта это будет закрыто scope-ом "items:write:any", 
но мы ещу раз проверим через current_user.can, чтобы сервис был устойчивым.
'''

async def change_item_owner(
    session: AsyncSession,
    current_user: AccessUser,
    item_id: UUID,
    new_owner_id: UUID
) -> Item | None:
    # доп. защита на уровне сервиса
    if not current_user.can("items", "write"):
        return None
    
    item = await items_repo.get_item(session=session, item_id=item_id)
    if item is None:
        return None
    
    new_owner = await users_repo.get_user(session=session, user_id=new_owner_id)
    if new_owner is None:
        return None
    
    # используем репозиторий, где уже есть логика смены владельца через new_user
    return await items_repo.patch_item(
        session=session,
        item_db=item,
        # кладем пустой ItemUpdate, т.к. у нас только смена владельца
        item_data=ItemUpdate(),
        new_user=new_owner
    )

# -----------------------------------------------------------------------------------------------

# Внедрение сервисного слоя в код items-эндпоинтов

'''
Итак, сервисный слой для items готов, теперь будем внедрять его
в app/routes/items.py.

Для начала добавим импорт сервисного слоя:
'''

# app/routes/items.py
...
from app.services import items as items_service
...

'''
Затем убираем репозиторные импорты, которые больше не будут нужны:
'''

# УДАЛИТЬ
from app.repositories.items import get_item, delete_item, patch_item, list_items_with_count
from app.repositories.users import get_user

'''
Идем к эндпоинту GET /items/. Заменим вызов функции list_items_with_count() на следующее:
'''

@router.get('/', response_model=ItemsOut)
async def read_items(...):
    items, count = await items_service.get_items_with_count(
        session=session,
        current_user=current_user,
        q=q,
        limit=limit,
        offset=offset
    )

'''
И все, эндпоинт больше не работает с user_id. 
Теперь, если мы залогинимся как простой user и обратимся к GET /items/, то получим items
только данного пользователя! А если залогинимся под админом, то получим items всех пользователей!

Двигаемся к эндпоинту GET /items/{item_id}. Заменим вызов функции get_item() на следующее:
'''

@router.get("/{item_id}", response_model=ItemOut) 
async def read_item_by_id(...):
    item = await items_service.get_item_for_read(
        session=session,
        current_user=current_user,
        item_id=item_id
    )

'''
Теперь, если мы залогинимся как простой user и попробуем обратиться к чужому item, то увидим
статус 404, а при обращении к своему item - все окей. Под админом нам доступны все items.

Перейдем к эндпоинту PATCH /items/{item_id}. Новая логика работы будет следующая:
1) Получаем item через items_service.get_item_for_write()
2) Если сервис вернул None - отдаем статус 404.
3) В противном случае обновляем item
При этом мы удаляем всю логику по работе с user внутри эндпоинта, для этого будет
отдельный эндпоинт. Обновленное тело эндпоинта будет выглядеть так:
'''

@router.patch("/{item_id}", response_model=ItemOut) 
async def patch_item_by_id(...):
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

'''
При тестировании обновленной версии эндпоинта PATCH /items/{item_id} мы все-еще будем
видеть поле user_id. Можем на него не обращать внимание, оно будет игнорироваться сервисом.
При изменении item через простого user все сработает только для items конкретного user.
Для админа можно менять любые items.

Теперь перейдем к эндпоинту DELETE /items/{item_id}, схема изменения такая же, как и для
PATCH /items/{item_id}:
'''

@router.delete("/{item_id}")
async def delete_item_by_id(...):
    item_db = await items_service.get_item_for_write(
        session=session,
        current_user=current_user,
        item_id=item_id
    )
    if item_db is None:
        raise HTTPException(status_code=404, detail='Item not found')
    
    await items_service.delete_item(session=session, item_db=item_db)
    return {"status": "deleted"}

'''
Теперь, если простой user попытается удалить чужой item - увидит статус 404.
Свой item получится удалить без проблем. Админ может удалять любые items.

Остался еще один момент в работе с items-эндпоинтами.
Как мы уже говорили ранее, сейчас PATСH-запрос может менять владельца item,
потому что в модели ItemUpdate есть user_id. Получается не очень логичная ситуация,
т.к. "обновить поля item" не то же самое, что передать "передать item другому владельцу".
Поэтому мы разделим две операции:
- PATCH /items/{item_id} - изменять только поля item (title, description)
- PATCH /items/{item_id}/owner - отдельная админская операция смены владельца

Первым делом уберем поле user_id в модели ItemUpdate, которая находится в файле
app/models/items.py:
'''

# app/models/items.py
...
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=128)
...

'''
Теперь Swagger больше не покажет поле user_id в запросе PATCH /items/{id}.

Далее создадим отдельную SQLModel-модель для обновления именно ID владельца.
Назовем модель ItemOwnerUpdate:
'''
...
class ItemOwnerUpdate(SQLModel):
    user_id: UUID
...

'''
Теперь добавим новый эндпоинт в файл app/routes/items.py.
Для защиты доступа будем требовать scope "items:write:any".
Внутри будем вызывать функцию items_service.change_item_owner().
Если получим None - вернем статус 404, иначе вернем обновленный item.
И, конечно, не забудем импортировать модель ItemOwnerUpdate.
'''

# app/routes/items.py

...
from app.models.items import ItemOwnerUpdate
...
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

'''
Супер, теперь менять владельца item может только admin, как мы и хотели.
'''

# -----------------------------------------------------------------------------------------------

# Создание и внедрение минимального users-сервиса

'''
Сейчас почти все эндпоинты в app/routes/users.py у нас админские.
Но scopes "users:read:own" и "users:write:own" у нас уже есть и логично дать пользователю
минимальную возможность для работы со своими данными. Поэтому сейчас мы создадим 2 отдельных эндпоинта:
- GET /users/me - посмотреть данные о себе
- PATCH /users/me - поменять данные о себе (username, статус is_active)

Для реализации эти эндпоинтов внутри сервисного файла app/services/users.py создадим 2 функции,
пока в виде заголовков.

СОВЕТ ПРЕПОДАВАТЕЛЮ: рекомендуется параллельно писать код и рассказывать назначения
для каждой функции.

- get_me() - вернуть данные текущего авторизованного пользователя.
- patch_me() - обновить данные текущего пользователя по присланным полям,
с проверкой уникальности username перед сохранением.
'''

# app/services/users.py

async def get_me():
    '''
    Вернуть данные текущего авторизованного пользователя.
    '''


async def patch_me():
    '''
    Обновить данные текущего пользователя по присланным полям,
    с проверкой уникальности username перед сохранением.
    '''

'''
Заголовки функций готовы, теперь пропишем необходимые импорты:
'''

from sqlmodel.ext.asyncio.session import AsyncSession

from app.access import AccessUser
from app.models.users import User, UserUpdate
from app.repositories.users import get_user_by_username, update_user

'''
Теперь пропишем тело функции get_me(), где просто будем возвращать current_user.user:
'''

async def get_me(current_user: AccessUser) -> User:
    return current_user.user

'''
Теперь реализуем patch_me() с проверкой уникальности username, если его прислали.
После проверки загрузим текущего пользователя из БД, чтобы он существовал в этой сессии
и обновим его:
'''

async def patch_me(
    session: AsyncSession,
    current_user: AccessUser,
    user_in: UserUpdate
) -> User:
    if user_in.username:
        existing_user = await get_user_by_username(
            session=session, 
            username=user_in.username
        )
        if existing_user and existing_user.id != current_user.user.id:
            raise ValueError("Username already exists")
    
    db_user = await session.get(User, current_user.user.id)
    
    return await update_user(
        session=session,
        db_user=db_user,
        user_in=user_in
    )

'''
Минимальный сервис для users готов, теперь внедрим его в файл с эндпоинтам - app/routes/users.py.
Сначала импортируем сам сервис под псевдонимом users_service:
'''

# app/routes/users.py
...
from app.services import users as users_service
...

'''
Реализуем эндпоинт для обработки GET /users/me, где будем проверять scope "users:read:own"
и возвращать current_user.user:
'''

@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["users:read:own"])]
):
    return await users_service.get_me(current_user)

'''
Осталось реализовать эндпоинт для обработки PATCH /users/me, где будем пробовать выполнить обновление
данных пользователя, и в случае исключения ValueError выбрасывать HTTPException со статусом 409:
'''

@router.patch("/me", response_model=UserOut)
async def patch_me(
    user_in: UserUpdate, 
    session: SessionDep,
    current_user: Annotated[AccessUser, Security(get_current_user, scopes=["users:write:own"])]
):
    try:
        return await users_service.patch_me(
            session=session,
            current_user=current_user,
            user_in=user_in
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

# -----------------------------------------------------------------------------------------------

# Добавление возможности для user-а создавать свои items

'''
Остался финальный штрих - дать пользователю не только смотреть данные о себе и редактировать
имеющиеся items, но и создавать новые items для себя. Сейчас эндпоинт POST /users/{user_id}/items
является админским, поэтому создадим отдельный эндпоинт только для user:

- POST /items/ - создать item для текущего пользователя

Для реализации этого эндпоинта сначала внутри сервисного файла app/services/items.py создадим функцию
create_item(), использующую функцию create_item() из репозитория.
Чтобы не было проблем с сессиями, мы выгрузим текущего пользователя и через него создадим новый item.
'''

# app/services/items.py

...
from app.models.items import ItemCreate
...

async def create_item(
    session: AsyncSession,
    current_user: AccessUser,
    item_data: ItemCreate
) -> Item:
    '''
    Создать новый item для текущего пользователя.
    '''
    owner = await session.get(User, current_user.user.id)
    return await items_repo.create_item(
        session=session,
        user=owner,
        item_data=item_data
    )

'''
Сервисная функция готова, теперь внедрим ее в новом эндпоинте.
Пойдем в файл app/routes/items.py и создадим функцию create_item(),
которую защитим через scope "items:write:own":
'''

# app/routes/items.py

...
from app.models.items import ItemCreate
...

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


'''
Итак, эндпоинты готовы! Теперь текущий пользователь может получать информацию только о себе
и редактировать только свои данные. Мы проделали огромный труд, друзья и создали сложную систему
с аутентификацией, правами и доступами. Эти знания нам еще пригодятся на курсе 😉
'''