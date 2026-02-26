from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

ALGORITHM = "HS256"


password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher()
    )
)


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire
    }
    token = jwt.encode(
        payload=payload,            
        key=settings.SECRET_KEY,    
        algorithm=ALGORITHM         
    )
    return token


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    verified, updated_hash = password_hash.verify_and_update(
        plain_password,
        hashed_password
    )
    return verified, updated_hash