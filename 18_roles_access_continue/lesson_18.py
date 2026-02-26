# Проверка доступа в слоях приложения

# Объявление scopes в security-схеме

'''
В нашем проекте есть файл app/deps.py. В этом файле уже есть использование класса
OAuth2PasswordBearer. Помним, что с помощью этого класса мы читаем Bearer-токен 
из заголовка Authorization: Bearer ... и передаем его дальше, где вызывается зависимость.

Сейчас экземпляр класса OAuth2PasswordBearer создается так:
'''

# app/deps.py
...
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login/access-token")
...

'''
То есть сейчас указан только один параметр - tokenUrl (где находится эндпоинт выдачи токена).
Но именно здесь, дополнительным параметром, можно указать scopes для нашего проекта.
Для этого выше объявим словарь с названием SCOPES, где будет храниться описание прав
для документации проекта.
Ключ - имя scope, то есть строка, использующаяся как permission (например, "items:read:own").
Значение - понятное человеку описание, которое мы увидим в Swagger:
'''

# app/deps.py
...
SCOPES: dict[str, str] = {
    "items:read:own": "Чтение только своих items",
    "items:write:own": "Создание/изменение/удаление только своих items",
    "items:read:any": "Чтение items у любых пользователей",
    "items:write:any": "Создание/изменение/удаление items любых пользователей и смена владельца",

    "users:read:own": "Чтение только своих данных",
    "users:write:own": "Изменение только своих данных",
    "users:read:any": "Чтение данных любых пользователей",
    "users:write:any": "Создание/изменение/удаление любых пользователей"

}
...

'''
Словарь готов - возвращаемся к reusable_oauth2. Рядом с tokenUrl укажем параметр scopes
и передадим туда наш словарь SCOPES:
'''

# app/deps.py
...
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/login/access-token",
    scopes=SCOPES
)
...

'''
Таким образом, мы влияем на OpenAPI - FastAPI будет генерировать security scheme
вместе с переданными scopes. Если мы запустим приложение и нажмем кнопку Authorize,
то снизу увидим список чек-боксов с указанными нами scopes. Важно уточнить, что сейчас пока что:
- scopes не проверяются, мы их только объявили
- Эндпоинты по прежнему не требуют scopes
- В Swagger отображается список разрешений при аутентификации
'''

# --------------------------------------------------------------------------------------

# Сохранение scopes в JWT-токене

'''
Перейдем к коду. Сначала формально зафиксируем соответствие ролей и scopes.
Для этого откроем файл app/core/security.py и добавим вверху словарь ROLE_TO_SCOPES,
для сопоставления ролей и прав для этих ролей. Ключ - имя роли в виде строки "user" или "admin",
значение - множество scopes, которые доступны в этой роли. Мы используем именно множество по 2-м причинам:
- Отсутствие дубликатов прав
- Удобно объединять права, если у пользователя несколько ролей
'''

# app/core/security.py
...
ROLE_TO_SCOPES: dict[str, set[str]] = {
    "user": {
        "items:read:own",
        "items:write:own",
        "users:read:own",
        "users:write:own"
    },
    "admin": {
        "items:read:any",
        "items:write:any",
        "users:read:any",
        "users:write:any"
    }
}
...

'''
Ниже создадим специальную функцию scopes_for_roles(), которая собирает scopes
согласно указанным ролям. Она будет объединять все scopes в единое множество
строк и возвращать отсортированный список, что удобно для логов и тестирования кода.
'''

def scopes_for_roles(role_names: list[str]) -> list[str]:
    scopes: set[str] = set()
    for role in role_names:
        scopes.update(ROLE_TO_SCOPES.get(role, set()))
    return sorted(scopes)

'''
Двигаемся дальше. Сейчас наш токен содержит только поля 'sub' и 'exp'.
Это видно по объекту payload внутри функции create_access_token().
Давайте расширим payload, добавив внутри поле 'scope' со значением scope, являющееся является строкой,
которую мы также будем принимать в качестве аргумента функции create_access_token().
Так принято в стандарте OAuth2, где scope - это одна строка, содержащая внутри много
scopes через пробел. Причем значение по умолчанию для нашей строки scope будет пустая строка, 
т.к. это необязательная часть токена для всех сценариев.
'''

def create_access_token(...):
    ...
    payload = {
        "sub": str(subject),
        "exp": expire,
        "scope": scope
    }
    ...

'''
С файлом app/core/security.py разобрались, двигаемся дальше.

Откроем файл app/routes/login.py. Внутри есть реализованная нами функция login_access_token()
для обработки запроса POST /login/access-token. Нам нужно доработать эту функцию следующим образом:

1) Пользователь ввел логин и пароль - получаем объект user 
2) Получаем роли этого пользователя из БД
3) По словарю ROLE_TO_SCOPES собираем scopes
4) Кладем scopes в JWT-токен и возвращаем его
Так приложение будет понимать кто именно пришел и выдавать пользователю соответствующие роли права 😎

Вверху файла добавим необходимые импорты:
'''

# app/routes/login.py
...
from sqlmodel import select
...
from app.models.roles import Role, UserRoleLink
from app.core.security import scopes_for_roles
...

'''
Затем, внутри функции login_access_token(), после получения и валидации объекта user, добавим:
- получение ролей пользователя (user) из таблиц roles и user_roles
- получение списка scopes для полученных ролей
- сборку итоговой строки scopes для будущего сохранения в токен
'''

...
async def login_access_token(...):
    ...
    stmt_roles = (
        select(Role.name)
        .join(UserRoleLink, Role.id == UserRoleLink.role_id)
        .where(UserRoleLink.user_id == user.id)
    )
    role_names = (await session.exec(stmt_roles)).all()
    scopes_list = scopes_for_roles(role_names)
    scope_str = " ".join(scopes_list)
    ...

'''
Осталось внедрить scope при создании токена:
'''

...
async def login_access_token(...):
    ...
    return Token(
        access_token=create_access_token(
            subject=user.id, 
            expires_delta=access_token_expires,
            scope=scope_str
        )
    )

'''
С app/routes/login.py разобрались, осталось внести небольшие правки
в модель TokenPayload, которая хранится у нас в app/models/tokens.py.
К существующему полю 'sub' добавим поле 'scope' в виде строки, значение
по умолчанию также будет пустой строкой:
'''

# app/models/tokens.py

class TokenPayload(SQLModel):
    sub: str | None = None
    scope: str = ""

'''
Теперь запустим приложение, обратимся к эндпоинту POST /login/access-token,
в поле username введем admin, в поле password введем Admin12345678,
в scope ничего вводить не будем, оставим галочку в пункте "Send empty value".
После выполнения запроса в теле ответа мы увидим подобное:

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
  eyJzdWIiOiJhZmRlNzliYi1mMWNjLTRhOTQtOTNmYi0xNDc3YzE2NjQxZTUiLCJleHAiOjE3NzIwM
  DIyNTUsInNjb3BlIjoiaXRlbXM6cmVhZCBpdGVtczp3cml0ZSB1c2VyczpyZWFkIHVzZXJzOndyaXRlIn0.
  qJ0IcQVzQavjngamFTqONRoiM45BmPzYGzla_74IUVA",
  "token_type": "bearer"
}

Попробуем декодировать полученный JWT-токен и посмотреть его содержимое.
Для простоты можно перейти на сайт https://www.jwt.io/ и слева, в поле "JSON Web Token (JWT)",
вставить наш JWT-токен. Справа, в разделе "Decoded Payload" появится декодированное содержимое нашего токена,
где будут "sub", "exp" и "scope", где лежит строка с разрешениями 
для админа ("items:read items:write users:read users:write"), как мы и хотели!

В результате, мы связали RBAC и OAuth2 так, что:
- Роли хранятся в БД
- При аутентификации роль превращается в scopes
- scopes сохраняются в JWT-токен в виде строки
'''

# --------------------------------------------------------------------------------------

# Проверка scopes в get_current_user() через SecurityScopes

'''
Следующий шаг - научить зависимость get_current_user() из файла app/deps.py 
понимать, какие scopes требует эндпоинт, и сравнивать их с теми, что лежат в токене.
Для этого в FastAPI существует специальный класс - SecurityScopes. Он собирает
все требуемые scopes для цепочки зависимостей эндпоинта. С помощью SecurityScopes
можно проверять, имеет ли пользователь все необходимые scopes для доступа к эндпоинту.
Импортируем этот класс в app/deps.py:
'''

# app/deps.py
...
from fastapi.security import SecurityScopes
...

'''
Далее двинемся к заголовку функции get_current_user().
Сейчас она принимает 2 аргумента - session и token. Добавим третий - security_scopes: SecurityScopes.
Так FastAPI будет автоматически передавать сюда "какие scopes требуются" при вызове get_current_user()
как функции зависимости:
'''
...
async def get_current_user(
    session: SessionDep,
    security_scopes: SecurityScopes,
    token: TokenDep,
) -> User:
    ...

'''
Далее в самое начало тела функции добавим проверку - если эндпоинт требует scopes,
то добавим их в специальный объект authenticate_value. Если не требует - сохраним туда
просто строку "Bearer". Также сразу ниже объявим отдельно исключение credentials_exception,
которое будем вызывать при проблемах с валидацией токена. Внутри этого исключения дополнительно
укажем заголовок "WWW-Authenticate", а возвращаемый статус будет 401, как это принято в стандарте OAuth2.
'''

async def get_current_user(...):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = f"Bearer"
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value}
    )
'''
Теперь ниже в коде, при обработке исключений InvalidTokenError и ValidationError,
мы можем вызывать исключение credentials_exception. Также, если в token_data
не окажется поля 'sub', значит тоже следует вызвать исключение credentials_exception:
'''

async def get_current_user(...):
    ...
    try:
        ...
    except (InvalidTokenError, ValidationError):
        raise credentials_exception
    if not token_data.sub:
        raise credentials_exception

'''
Финальный шаг - проверка, что scopes из токена совпадают со всеми scopes из security_scopes.
Если найдем хотя бы одно расхождение - вызываем исключение со статус 401 и сообщением "Not enough permissions":
'''

async def get_current_user(...):
    ...
    token_scopes = token_data.scope.split()
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=401,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value}
            )

'''
Теперь наша зависимость get_current_user() умеет читать scopes из токена и сравнивать их с теми,
что требует эндпоинт. Это стало возможно через класс SecurityScopes.
'''

# --------------------------------------------------------------------------------------

# Подключение scopes к эндпоинтам

'''
Последний шаг сегодняшнего занятия - сделаем наши эндпоинты непубличными и начнем требовать scopes.
Важно - сейчас мы будем защищать эндпоинты именно через scopes, а значит нам важно следующее:
- Эндпоинт требует scope
- Токен проверяется через get_current_user()
- Swagger начинает показывать требования прав на эндпоинтах

Главный плюс заключается в удобстве - мы не будем переписывать тела функций.
Мы просто добавим dependencies в декораторы с использованием новой функции - Security().
C помощью нее можно создавать зависимости, как и через Depends(), но с той лишь разницей,
что Security() может объявлять scopes по стандарту OAuth2. Начнем с файла app/routes/items.py,
где сначала импортируем Security(), а также функцию get_current_user(), она пригодится
при использовании Security():
'''

# app/routes/items.py

...
from fastapi import Security

from app.deps import get_current_user
...

'''
Теперь в каждом декораторе @router укажем соответствующий scope через параметр dependencies,
передав в него список из одного элемента - результат работы функции Security() с параметрами 
get_current_user и scopes внутри. Важно - везде будем передавать scope с own на конце,
чтобы эти эндпоинты были доступны как обычным пользователям, так и админам.

СОВЕТ ПРЕПОДАВАТЕЛЮ: для ускорения можно просто копировать и вставлять строчку
Security(get_current_user, scopes=["..."]), вписывая нужный scope.
'''

@router.get(
    '/', 
    dependencies=[Security(get_current_user, scopes=["items:read:own"])],
    response_model=ItemsOut
)
async def read_items(...):
    ...

@router.get(
    "/{item_id}",
    dependencies=[Security(get_current_user, scopes=["items:read:own"])],
    response_model=ItemOut
)           
async def read_item_by_id(...):
    ...

@router.patch(
    "/{item_id}", 
    dependencies=[Security(get_current_user, scopes=["items:write:own"])],
    response_model=ItemOut
)             
async def patch_item_by_id(...):
    ...

@router.delete(
    "/{item_id}",
    dependencies=[Security(get_current_user, scopes=["items:write:own"])]
)
async def delete_item_by_id(...):
    ...

'''
С файлом app/routes/users.py будет чуть иначе:
- регистрацию через POST /users/ оставим публичной, чтобы любой пользователь извне мог зарегистрироваться
- остальные эндпоинты пока что сделаем доступными только для админа. Это временная мера,
т.к. сейчас некоторые оставшиеся эндпоинты принимают ID в качестве ресурса URL.
А если просто навесить scope уровня "own" без дополнительных проверок, то 
пользователь сможет подставить чужой ID и получить доступ к чужим данным. 
'''

# app/routes/users.py

...
from fastapi import Security

from app.deps import get_current_user
...


@router.post(
    "/{user_id}/items",
    dependencies=[Security(get_current_user, scopes=["items:write:any"])]
)
async def create_user_item(...):
    ...


@router.get(
    "/", 
    dependencies=[Security(get_current_user, scopes=["users:read:any"])],
    response_model=UsersOut
)
async def read_users(...):
    ...


@router.get(
    "/{user_id}", 
    dependencies=[Security(get_current_user, scopes=["users:read:any"])],
    response_model=UserOut
)
async def get_user_by_id(...):
    ...


@router.get(
    "/{user_id}/items",
    dependencies=[Security(get_current_user, scopes=["users:read:any"])],
    response_model=ItemsOut
)
async def get_user_items(...):
    ...


@router.patch(
    "/{user_id}", 
    dependencies=[Security(get_current_user, scopes=["users:write:any"])],
    response_model=UserOut
)
async def patch_user(...):
    ...


@router.delete(
    "/{user_id}",
    dependencies=[Security(get_current_user, scopes=["users:write:any"])]
)
async def delete_user_by_id(...):
    ...

'''
Теперь, если мы запустим приложением, то увидим, что почти все эндпоинты защищены "замочками"
и без ввода username с password ими воспользоваться не получится.

На дальнейших занятиях-воркшопах мы будем улучшать наш проект, дорабатывая роли и доступы с 
соблюдение чистой архитектуры веб-приложений.
'''