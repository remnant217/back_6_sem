from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from enum import StrEnum

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.users import User


class RoleName(StrEnum):
    USER = "user"
    ADMIN = "admin"


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