from datetime import datetime
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.job import JobDB, JobStatus, JobCreate


async def create_job(session: AsyncSession, data: JobCreate) -> JobDB:
    job = JobDB(title=data.title)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: UUID) -> JobDB | None:
    return await session.get(JobDB, job_id)


async def set_status(
    session: AsyncSession,
    job: JobDB,
    status: JobStatus,
    finished_at: datetime | None = None,
    error: str | None = None,
) -> JobDB:
    job.status = status
    if finished_at is not None:
        job.finished_at = finished_at
    if error is not None:
        job.error = error

    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job