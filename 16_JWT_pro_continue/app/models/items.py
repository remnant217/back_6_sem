from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.users import User

class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)

class ItemCreate(ItemBase):
    pass

class ItemOut(ItemBase):
    id: UUID
    user_id: UUID

class ItemsOut(SQLModel):
    data: list[ItemOut]
    count: int

class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    user_id: UUID | None = None

class Item(ItemBase, table=True):
    __tablename__ = 'items'
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key='users.id', 
        nullable=False, 
        ondelete="CASCADE"
    )
    user: "User" = Relationship(back_populates='items')