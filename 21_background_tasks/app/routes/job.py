from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger

from app.core.database import SessionDep
from app.models.job import JobOut, JobCreate
from app.repositories.job import get_job, create_job
from app.tasks.job import run_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobOut)
async def create_job_endpoint(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> JobOut:
    job = await create_job(session, payload)
    logger.info(f'Sheduling background task for job_id = {job.id}')
    background_tasks.add_task(run_job, job.id)

    return JobOut(
        id=job.id,
        title=job.title,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error=job.error,
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job_endpoint(
    job_id: UUID,
    session: SessionDep,
) -> JobOut:
    job = await get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobOut(
        id=job.id,
        title=job.title,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error=job.error,
    )
