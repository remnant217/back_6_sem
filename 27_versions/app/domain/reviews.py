from dataclasses import dataclass
from uuid import UUID


class DomainError(ValueError):
    """Ошибка доменной валидации."""


@dataclass(frozen=True)
class Review:
    id: UUID | None
    book_id: UUID
    rating: int
    text: str | None

    def __post_init__(self) -> None:
        if not (1 <= self.rating <= 5):
            raise DomainError("Рейтинг должен быть в диапазоне от 1 до 5 включительно.")

        if self.text is not None:
            t = self.text.strip()
            if not t:
                object.__setattr__(self, "text", None)
            elif len(t) > 2000:
                raise DomainError("Длина отзыва не должна превышать 2000 символов.")
            else:
                object.__setattr__(self, "text", t)
