from sqlalchemy import Column, Integer, String, Boolean
from pydantic import BaseModel, ConfigDict, Field
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    is_active: bool = True

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)