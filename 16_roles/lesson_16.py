# Доработка JWT-авторизации

# Создание моделей токенов

'''
Основной фокус доработки JWT-авторизации сосредоточим на токенах. В предыдущем семестре мы уже работали
с подобным кодом, поэтому часть информации будет для вас знакомой. Для начала в папке models/ создадим
новый файл - tokens.py, где будем хранить следующие модели для работы с токенами:
- Token - данные, которые возвращается клиенту после успешной авторизации (сам токен доступа и тип токена)
- TokenPayload - данные, которые мы ожидаем увидеть внутри JWT-токена при его получении (у нас это будет только sub,
может быть необязательным по спецификации JWT)
'''

# app/models/tokens.py

from sqlmodel import SQLModel

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(SQLModel):
    sub: str | None = None

# ----------------------------------------------------------------------------------------------------

# Создание отдельного файла с зависимостями

'''
С новыми моделями закончили, следующий шаг - создать отдельный файл для хранения зависимостей.
Так мы делали в предыдущем семестре, сделаем и сейчас. В папке app/ создадим новый - файл deps.py.
В файле будут находиться 3 зависимости:
- SessionDep - зависимости для работы с БД
- TokenDep - зависимость для работы с токенами
- CurrentUser - зависимость для получения пользователя из БД по токену
И да, обратите внимание, что мы перенесем зависимость SessionDep из файла app/database.py сюда,
в app/deps.py.
'''

# app/deps.py

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.tokens import TokenPayload
from app.models.users import User


# переносим зависимость SessionDep в данный файл
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# создаем зависимость для работы с bearer-токенами
# в tokenUrl указываем адрес эндпоинта, где в будущем будем брать токен
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login/access-token")

TokenDep = Annotated[str, Depends(reusable_oauth2)]


# создаем зависимость для получения пользователя из БД по токену
async def get_current_user(session: SessionDep, token: TokenDep) -> User:
    # пробуем декодировать токен и выгрузить sub в переменную token_data
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    # если при декодировании токена возникла проблема
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials"
        )
    # выгружаем пользователя из БД по ID из поля sub
    user = await session.get(User, token_data.sub)
    # если такого пользователя нет в БД
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # если пользователь есть в БД, но он неактивен
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

'''
Т.к. мы перенесли SessionDep в этот файл, то обновим импорты этой зависимости
во всех файлах папки routes/, где используется данная зависимость.

СОВЕТ ПРЕПОДАВАТЕЛЮ: пройдитесь по файлам в папке routes/ и замените строчку
from app.database import SessionDep на from app.deps import SessionDep.
'''

# ----------------------------------------------------------------------------------------------------

# Создание репозиторной функции для аутентификации пользователя

'''
С зависимостями разобрались, теперь пойдем к репозиторному слою. В файле app/repositories/users.py
добавим новую функцию authenticate_user() для получения пользователя по username и password.
'''

# app/repositories/users.py

...
from app.core.security import verify_password

...
async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str
) -> User | None:
    user = await get_user_by_username(session, username)
    # если пользователя с таким username нет в БД
    if user is None:
        return None
    # если пользователь есть - проверяем его пароль
    verified, updated_hash = verify_password(password, user.hashed_password)
    # если пароль не совпал
    if not verified:
        return None
    # если получили новый хэш из-за нового алгоритма хэширования - обновляем его в БД
    if updated_hash:
        user.hashed_password = updated_hash
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

# ----------------------------------------------------------------------------------------------------

# Создание эндпоинтов для работы с токенами

'''
Репозиторная функция готова, двигаемся дальше - к эндпоинтам. В папке routes/ создадим новый файл - login.py.
Внутри файла мы создадим функции для обработки двух эндпоинтов:
- POST /login/access-token - получение токена доступа. Это POST-запрос, т.к. по стандарту OAuth2 
токен запрашивают именно POST-запросом - мы отправляем данные для входа и получаем новый токен.
- POST /login/test-token - тестирование токена через получение данных об пользователе. 
Это защищенный запрос, доступный только для авторизованных пользователей. К тому же, это также POST-запрос, 
т.к. реализуется проверочная auth-операция для валидации токена. В реальных проектах можно увидеть практику,
что все login-действия реализуются единообразно через POST, чтобы избежать нюансов с кэшированием и логированием,
а также случайными GET-вызовами.
'''

# app/routes/login.py

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_access_token
from app.deps import CurrentUser, SessionDep
from app.models.tokens import Token
from app.models.users import UserOut
from app.repositories.users import authenticate_user

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/access-token", response_model=Token)
async def login_access_token(
    session: SessionDep,
    # данные формы OAuth2 (в нашем случае - username и password)
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    user = await authenticate_user(session, form_data.username, form_data.password)
    # если аутентификация не пройдена
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    # если учетная запись пользователя неактивна
    elif not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    # вычисляем срок действия токена доступа
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=create_access_token(
            subject=user.id, 
            expires_delta=access_token_expires
        )
    )


@router.post("/test-token", response_model=UserOut)
async def test_token(current_user: CurrentUser):
    return current_user

'''
Важный момент - чтобы мы могли корректно извлекать username и password из формы, нам понадобится
модуль python-multipart. Мы с ним уже работали в предыдущем семестре, установим его и сейчас:

В терминале:

pip install python-multipart

Новый роутер с двумя эндпоинтами готов, теперь подключим его в app/main.py:
'''

# app/main.py

from app.routes.login import router as login_router
...
app.include_router(login_router)