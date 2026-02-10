# Продвинутое использование JWT-токенов

# Настройка секретного ключа

'''
Сейчас мы будем настраивать секретный ключ (SECRET_KEY) для нашего проекта, чтобы выдаваемые
токены была стабильными и не ломались после перезапуска сервера.

Создадим .env-файл в корне нашего проекта и напишем там строку:
'''

# .env

SECRET_KEY=...

'''
Само значение ключа мы сгенерируем знакомы с предыдущего семестра способом - через встроенный
модуль secrets. В отдельном файле или интерактивной среде импортируем secrets и с помощью
функции token_hex() сгенерируем себе ключ:
'''

# В отдельном файле или интерактивной среде

from secrets import token_hex

print(token_hex(32))

'''
Скопируем полученный ключ и сохраним к себе в .env-файл:
'''

# .env

SECRET_KEY=f9fce53031123570ce2597a756451c42d0cfc4b1bde0fda62301ee476a936168

# -----------------------------------------------------------------------------------------

# Создание файла конфигурации

'''
Выше мы сохранили секретный ключ в .env-файл. Теперь создадим файл с конфигурацией нашего проекта.
Ранее на курсе мы научились работать с модулем pydantic-settings, его и будем использовать.
Для начала убедимся, что он установлен в виртуальном окружении нашего проекта. 

В терминале:

pip install pydantic-settings

Далее внутри папки app/ создадим папку core/, где создадим файл config.py, именно там будем
прописывать конфигурацию нашего проекта.
'''

# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()

'''
Давайте убедимся, что секретный ключ действительно загружается в программу, а
а поля SECRET_KEY и ACCESS_TOKEN_EXPIRE_MINUTES доступны для чтения.
'''

# В терминале или интерактивной среде:

from app.core.config import settings

print(f'Секретный ключ загружен: {settings.SECRET_KEY}')
print(f'Время жизни токена: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}')

# -----------------------------------------------------------------------------------------

# Создание функций для работы с токенами и паролями

'''
В папке core/ создадим файл security.py.

Перед написанием кода в файле security.py, установим необходимые библиотеки для работы
с JWT-токенами и шифрованием паролей. В прошлом семестре мы использовали библиотеки pyjwt
и pwdlib, установим их:

В терминале:

pip install pyjwt "pwdlib[argon2]"
'''

# app/core/security.py

# подключаем инструменты для работы со временем действия токена доступа
from datetime import datetime, timedelta, timezone
# подключаем тип Any, чтобы указать, что ID пользователя может прийти не только в виде строки
from typing import Any

# импортируем инструменты для работы с хэшированием
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# импортируем объект с настройками конфигурации проекта
from app.core.config import settings

ALGORITHM = "HS256"

# указываем стратегию работы с хэшами - сначала будет работать Argon2Hasher,
# но если есть старые хэши, сделанные, например, через BcryptHasher - они тоже будут работать
# это полезно при миграции с одного алгоритма хэширования на другой, 
# чтобы старые хэши не ломались (нередкая практика в реальных проектах)

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher()
    )
)


# subject - идентификатор пользователя (может быть UUID, int, str, поэтому указываем | Any)
# expires_delta - время жизни токена
def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    # вычисляем момент, когда токен перестанет работать
    # используем UTC-время, чтобы не было проблемы с часовыми поясами
    expire = datetime.now(timezone.utc) + expires_delta

    # формируем полезную нагрузку токена
    payload = {
        # по стандарту JWT название "sub" часто используют как "кому принадлежит токен"
        "sub": str(subject),
        # PyJWT умеет работать с datetime и сам преобразует его
        "exp": expire
    }

    # подписываем токен секретным ключом, чтобы клиент не мог подделать содержимое payload
    token = jwt.encode(
        payload=payload,            # данные токена
        key=settings.SECRET_KEY,    # секретный ключ
        algorithm=ALGORITHM         # алгоритм подписи
    )

    return token


# получить хэш пароля
def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


# проверка пароля и обновление хэша при необходимости
def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    # проверка валидности пароля (False, True) 
    # и нужно ли обновлять хэш для надежности (None, "<новый_хэш>")
    verified, updated_hash = password_hash.verify_and_update(
        plain_password,
        hashed_password
    )
    return verified, updated_hash

# -----------------------------------------------------------------------------------------

# Первичное внедрение JWT-авторизации в проект

'''
Нам нужно модифицировать модели в файле app/models/users.py, добавив
в класс User поле hashed_password, а в модель UserCreate - поле password:
'''

# app/models/users.py

...
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


...
class User(UserBase, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(
        back_populates="user",
        passive_deletes="all"
    )

'''
С моделями разобрались, теперь отредактируем слой репозитория. Пойдем в файл app/repositories/users.py
и модифицируем функцию create_user():
'''

# app/repositories/users.py

...
# добавляем импорт функции для получения хэша
from app.core.security import get_password_hash

...
async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    # получаем хэш из переданного пароля
    hashed_password = get_password_hash(user_data.password)
    # создаем пользователя - берем все, кроме password
    data = user_data.model_dump(exclude={"password"})
    new_user = User(**data, hashed_password=hashed_password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

'''
Осталось протестировать создание пользователя с учетом всех обновлений.
Если мы запустим приложение и попробуем создать пользователя через эндпоинт POST /users/,
то увидим ошибку в терминале: "столбец "hashed_password" в таблице "users" не существует".

Делаем вывод - нужно создать и выполнить миграцию, т.к. мы изменили структуру класса User,
добавив поле hashed_password. Создадим и применим новую миграцию:

В терминале:

alembic revision --autogenerate -m "add hashed_password to users"
alembic upgrade head

И снова беда - при выполнении миграции появилась ошибка:
"столбец "hashed_password" отношения "users" содержит значения NULL".
Оно и логично - для существующих пользователей, у которых нет пароля, нет и хэша,
а пустым этот столбец быть не может. Чтобы исправить эту проблему, мы откроем файл миграции
..._add_hashed_password_to_users.py и подправим его:
'''

# ..._add_hashed_password_to_users.py
...
HASH_EXAMPLE = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"

def upgrade() -> None:
    # для колонки hashed_password сделаем nullable=True
    op.add_column('users', sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # заполняем все существующие строки, где hashed_password равен NULL
    op.execute(f"UPDATE users SET hashed_password = '{HASH_EXAMPLE}' WHERE hashed_password IS NULL")

    # делаем hashed_password снова nullable=False
    op.alter_column("users", "hashed_password", nullable=False)

'''
Файл миграции отредактирован, попробуем снова применить миграцию.

В терминале:
alembic upgrade head

Миграция сработала! Если мы сейчас зайдем в DBeaver, то в таблице users увидим новый столбец 
hashed_password. И для каждого пользователя проставился указнный нами хэш.
'''