from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.items import Item

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, min_length=1, max_length=64)
    is_active: bool = True

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: UUID

# модель для возврата списка пользователей
class UsersOut(SQLModel):
    data: list[UserOut]
    count: int

# модель для частичного обновления данных пользователя
class UserUpdate(SQLModel):
    username: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None

class User(UserBase, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    items: list["Item"] = Relationship(
        back_populates="user",
        passive_deletes="all"
    )