from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

ALGORITHM = "HS256"

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

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher()
    )
)


def scopes_for_roles(role_names: list[str]) -> list[str]:
    scopes: set[str] = set()
    for role in role_names:
        scopes.update(ROLE_TO_SCOPES.get(role))
    return sorted(scopes)


def create_access_token(
    subject: str | Any, 
    expires_delta: timedelta,
    scope: str = ""
) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "scope": scope
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