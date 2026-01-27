from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import ClassVar
from uuid import UUID


class BookGenre(StrEnum):
    """Допустимые жанры книги."""
    SCIENCE = "science"
    FANTASY = "fantasy"
    BIOGRAPHY = "biography"
    HISTORY = "history"


class DomainError(Exception):
    """Любая ошибка доменного слоя, возникающая при нарушении бизнес-правил."""


class InvalidYearError(DomainError):
    """Год издания книги вне допустимого диапазона"""
    def __init__(self, year: int, min_year: int, max_year: int) -> None:
        super().__init__(f"Год {year} вне диапазона [{min_year}, {max_year}]")
        self.year = year
        self.min_year = min_year
        self.max_year = max_year


@dataclass(eq=False)
class Book:
    """Доменная сущность 'Книга' с базовыми инвариантами и методами изменения."""

    # Идентификатор сущности, может быть None до сохранения в БД
    id: UUID | None
    # Обязательные данные книги
    title: str
    author: str
    published_year: int
    genre: BookGenre
    # Необязательные данные книги
    description: str | None = None
    page_count: int | None = None

    # Константы домена, не являются полями экземпляра класса
    MIN_YEAR: ClassVar[int] = 1000
    MAX_TITLE_LEN: ClassVar[int] = 200
    MAX_AUTHOR_LEN: ClassVar[int] = 120
    MAX_DESCRIPTION_LEN: ClassVar[int] = 5000

    # Приводим данные к единому формату и проверяем инварианты при создании объекта
    def __post_init__(self) -> None:
        self.title = self._norm_required(self.title, "title", self.MAX_TITLE_LEN)
        self.author = self._norm_required(self.author, "author", self.MAX_AUTHOR_LEN)
        self.published_year = self._validate_year(self.published_year)
        self.description = self._norm_optional(self.description, "description", self.MAX_DESCRIPTION_LEN)
        self.page_count = self._validate_page_count(self.page_count)

    # Публичные операции над сущностью

    def rename(self, new_title: str) -> None:
        self.title = self._norm_required(new_title, "title", self.MAX_TITLE_LEN)

    def change_author(self, new_author: str) -> None:
        self.author = self._norm_required(new_author, "author", self.MAX_AUTHOR_LEN)

    def change_published_year(self, new_year: int) -> None:
        self.published_year = self._validate_year(new_year)
    
    def change_genre(self, new_genre: BookGenre) -> None:
        self.genre = new_genre

    def change_description(self, new_description: str | None) -> None:
        self.description = self._norm_optional(new_description, "description", self.MAX_DESCRIPTION_LEN)

    def change_page_count(self, new_page_count: int | None) -> None:
        self.page_count = self._validate_page_count(new_page_count)

    # Внутренние методы для валидации и преобразования полей

    @classmethod
    def _validate_year(cls, year: int) -> int:
        """Год издания не может быть меньше MIN_YEAR и больше текущего года."""
        current_year = datetime.now(timezone.utc).year
        if year < cls.MIN_YEAR or year > current_year:
            raise InvalidYearError(year, cls.MIN_YEAR, current_year)
        return year

    @staticmethod
    def _validate_page_count(page_count: int | None) -> int | None:
        """Количество страниц в книге должно быть положительным, если задано."""
        if page_count is None:
            return None
        if page_count <= 0:
            raise DomainError("page_count должен быть положительным числом")
        return page_count

    @staticmethod
    def _norm_required(value: str, field_name: str, max_len: int) -> str:
        """
        Преобразование обязательного текстового поля:
        - Убираем пробельные символы
        - Проверяем на пустоту
        - Ограничиваем длину
        """
        value = (value or "").strip()
        if not value:
            raise DomainError(f"Поле '{field_name}' не может быть пустым")
        if len(value) > max_len:
            raise DomainError(f"Поле '{field_name}' слишком длинное (>{max_len})")
        return value

    @staticmethod
    def _norm_optional(value: str | None, field_name: str, max_len: int) -> str | None:
        """
        Преобразование необязательного текстового поля:
        - Если пустое - оставляем пустым
        - Иначе убираем пробельные символы и ограничиваем длину
        """
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > max_len:
            raise DomainError(f"Поле '{field_name}' слишком длинное (>{max_len})")
        return value