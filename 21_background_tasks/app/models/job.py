from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class JobCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)


class JobOut(SQLModel):
    id: UUID
    title: str
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None
    error: str | None


class JobDB(SQLModel, table=True):
    __tablename__ = "jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=200)

    status: JobStatus = Field(default=JobStatus.PENDING)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True))
    
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True))
    
    error: str | None = Field(default=None, max_length=2000)