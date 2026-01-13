from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# SQLAlchemy-модель таблицы с товарами
class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, default=0.0, nullable=False)
    in_stock = Column(Boolean, default=True, nullable=False)

# базовая Pydantic-модель товара
class ItemBase(BaseModel):
    name: str
    description: str | None = None
    price: float
    in_stock: bool = True

# модель для создания товара
class ItemCreate(ItemBase):
    pass

# модель для частичного обновления товара
class ItemUpdate(Base):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    in_stock: bool | None = None

# модель для возвращения ответа API
class ItemOut(ItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)