from dataclasses import dataclass
from uuid import UUID

from app.models.users import User


@dataclass
class AccessUser:
    user: User
    scopes: list[str]

    def can(self, resource: str, action: str, owner_id: UUID | None = None) -> bool:
        if f"{resource}:{action}:any" in self.scopes:
            return True
        if owner_id is not None and owner_id == self.user.id:
            return f"{resource}:{action}:own" in self.scopes
        return False