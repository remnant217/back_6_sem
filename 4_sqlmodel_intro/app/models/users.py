from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

# модель с общими свойствами для остальных моделей
class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, min_length=1, max_length=64)
    is_active: bool = True

# оставляем без изменений
class UserCreate(UserBase):
    pass

# модифицируем id и убираем ConfigDict()
class UserOut(UserBase):
    id: UUID

# наследуемся от UserBase, table=True показывает, что эта модель нужна для БД
class User(UserBase, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)