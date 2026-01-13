# SQLModel и CRUD-операции

# Внедрение UUID в репозиторий и роутер 
'''
Начнем исправление данной проблемы с файла app/repositories/users.py.
Для начала актуализируем импорты:
'''

# app/repositories/users.py

from sqlalchemy.ext.asyncio import AsyncSession
# ↓
# подключаем класс UUID и меняем sqlalchemy на sqlmodel для единого стиля кода
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession

'''
Теперь для поля user_id вместо int укажем UUID:
'''
async def get_user(session: AsyncSession, user_id: int) -> User | None:
    ...
# ↓
async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    ...

'''
С репозиторием разобрались, теперь идем в файл app/routes/users.py.
Подключим класс UUID и укажем его для user_id в функциях get_users_by_id()
и delete_user_by_id():
'''

# app/routes/users.py

from uuid import UUID
...
async def get_users_by_id(user_id: int, session: SessionDep):
    ...
# ↓
async def get_users_by_id(user_id: UUID, session: SessionDep):
    ...

async def delete_user_by_id(user_id: int, session: SessionDep):
    ...
# ↓
async def delete_user_by_id(user_id: UUID, session: SessionDep):
    ...

# ---------------------------------------------------------------------------------------------------------

# Поиск пользователей с фильтрацией и пагинацией
'''
Для начала пойдем в файл app/models/users.py и создадим новую модель - UsersOut,
которая будет содержать поля data и count:
'''

# app/models/users.py

# модель для возврата списка пользователей 
class UsersOut(SQLModel):
    data: list[UserOut]     # текущая страница с учетом пагинации
    count: int              # общее число записей, подходящих под фильтры

'''
С app/models/users.py разобрались, теперь идем в app/repositories/users.py.
Чтобы count вычислялось правильно, мы должны считать его по тем же фильтрам,
что и список данных. Поэтому мы создадим дополнительную функцию _apply_users_filters(),
которая применяет одинаковые фильтры к любому запросу:
'''

# app/repositories/users.py

# применяем указанные фильтры к запросу
# stmt - select-выражение, к которому будем добавлять методы where()
# q - подстрока для поиска, может быть None
# is_active - фильтр по активности, может быть None
def _apply_users_filters(stmt, q: str | None, is_active: bool | None):
    # если is_active передан - применяем фильтр
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    
    # если подстрока для поиска передана - применяем фильтр
    if q:
        # убираем возможные пробельные символы по краям
        q = q.strip()
        # после strip() строка могла стать пустой, значит фильтр применять нельзя
        if q:
            # ilike() - сопоставление строки с указанным шаблоном без учета регистра
            # проверяем вхождение q в любую часть строки
            stmt = stmt.where(User.username.ilike(f'%{q}%'))
    
    # возвращаем итоговый вид запроса
    return stmt

'''
Далее создадим саму функцию для возвращения списка пользователей,
назовем ее list_users_with_count(). Внутри мы создадим два запроса:
- Получение списка пользователей только для текущей страницы 
- Подсчет общего количества пользователей с учетом фильтров
'''
# func - объект для использования функций БД в запросах (например, COUNT())
# select() - функция для выполнения SELECT-запроса 
from sqlmodel import func, select

# возвращаем список пользователей текущей страницы 
# и общее количество пользователей с учетом фильтрации
async def list_users_with_count(
    session: AsyncSession,      # сессия для работы с БД
    q: str | None,              # подстрока для поиска
    is_active: bool | None,     # фильтр по активности
    limit: int,                 # максимальное возвращаемое количество записей
    offset: int                 # сколько записей пропустить
) -> tuple[list[User], int]:
    
    # выбираем все строки с пользователями
    data_stmt = select(User)
    # применяем единые фильтры
    data_stmt = _apply_users_filters(data_stmt, q, is_active)
    # порядок вывода по username для стабильности и удобства
    data_stmt = data_stmt.order_by(User.username)
    # указываем сколько строк пропустить и сколько строк взять
    data_stmt = data_stmt.offset(offset).limit(limit)
    # выполняем запрос и получаем данные страницы
    data_result = await session.exec(data_stmt)
    users = data_result.all()

    # select(func.count()) - посчитать количество строк
    # select_from(User) - явно указываем таблицу, по которой считаем
    count_stmt = select(func.count()).select_from(User)
    # применяем единые фильтры
    count_stmt = _apply_users_filters(count_stmt, q, is_active)
    # выполняем запрос и получаем количество записей
    count_result = await session.exec(count_stmt)
    # one() - берем одно значение
    count = count_result.one()

    # возвращаем кортеж (данные текущей страницы, общее количество записей)
    return users, count

'''
С репозиторием закончили, теперь идем в файл app/routes/users.py для оформления
нового эндпоинта. Логика работы эндпоинта будет следующая:
1) Принимаем query-параметры q, is_active, limit, offset
2) Ставим ограничения для offset и limit (например, чтобы нельзя было запросить миллион строк)
3) Вызываем функцию из репозитория
4) Возвращаем UsersOut
'''
# app/routes/users.py

from fastapi import Query
from app.models.users import UsersOut
from app.repositories.users import list_users_with_count
...
@router.get("/", response_model=UsersOut)
async def read_users(
    session: SessionDep,
    q: str | None = Query(default=None, description="Поиск по username"),
    is_active: bool | None = Query(default=None, description="Фильтр активности"),
    limit: int = Query(default=20, ge=1, le=100, description="Количество записей на странице"),
    offset: int = Query(default=0, ge=0, description="Сколько записей пропустить")
):
    users, count = await list_users_with_count(session, q, is_active, limit, offset)
    return UsersOut(data=users, count=count)

'''
Эндпоинт оформлен, теперь внесем еще одну правку в файл app/database.py, чтобы
работа с асинхронными сессия в SQLModel работала корректно. Для этого у объекта
AsyncSessionLocal укажем параметр class_ со значением AsyncSession:
'''
# app/database.py

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
# ↓
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------------------------------------

# Обновление данных пользователя
'''
Реализуем еще одну операцию - PATCH-запрос на обновление данных пользователя.
Начнем с того, что в файле app/models/users.py создадим модель UserUpdate для
обновления username или статуса is_active. Т.к. мы работаем с PATCH-запросом,
то оба поля внутри модели будут опциональными:
'''

# app/models/users.py

# модель для частичного обновления данных пользователя
class UserUpdate(SQLModel):
    username: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None

'''
Модель реализована, теперь двигаемся к репозиторию в app/repositories/users.py. 
Сначала мы создадим функцию для  получения пользователя по username. 
Разберемся почему эта функция нужна в данной ситуации. 
Если нам приходит PATCH-запрос на обновление username, то
нужно убедиться, что такого username нет ни у кого из других пользователей.
'''

# app/repositories/users.py

# поиск пользователя по username
async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await session.exec(stmt)
    return result.first()

'''
Теперь реализуем саму функцию частичного обновления данных пользователя внутри БД.
Не забудем в начале импортировать модель UserUpdate.
'''

from app.models.users import UserUpdate
...
async def update_user(session: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
    # получаем только те поля, которые пришли в запросе
    user_data = user_in.model_dump(exclude_unset=True)
    # обновляем поля объекта
    db_user.sqlmodel_update(user_data)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

'''
C репозиторием разобрались, теперь идем в файл app/routes/users.py создавать
новый эндпоинт. Для начала актуализируем импорты:
'''

# app/routes/users.py

from app.models.users import UserUpdate, User
from app.repositories.users import get_user_by_username, update_user
...

'''
Теперь реализуем сам эндпоинт. В начале будем проверять наличие пользователя в БД.
Затем, если нужно обновить username, то проверяем, что в БД нет другого пользователя
с таким же username. В конце вносим изменения для пользователя и возвращаем
его обновленные данные:
'''

@router.patch('/{user_id}', response_model=UserOut)
async def patch_user(user_id: UUID, user_in: UserUpdate, session: SessionDep):
    # получаем пользователя по UUID
    db_user = await session.get(User, user_id)
    # если пользователь не найден - возвращаем ошибку
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')
    
    # если нужно обновить username - проверяем уникальность
    if user_in.username:
        # пробуем получим пользователя с указанными username
        existing_user = await get_user_by_username(session, user_in.username)
        # если такой пользователь есть и это другой пользователя - запрещаем менять username
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=409, detail='Username already exists')
    
    # обновляем указанные поля
    db_user = await update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user