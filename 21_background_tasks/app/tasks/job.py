from random import choice
from datetime import datetime, UTC
from uuid import UUID

from loguru import logger
import httpx

from app.core.database import AsyncSessionLocal
from app.models.job import JobStatus
from app.repositories.job import get_job, set_status

# список URL, по которым будем отправлять GET-запросы, можно дополнить своими вариантами
URLS: list[str] = [
    "https://jsonplaceholder.typicode.com/todos/1",     
    "https://httpbin.org/get",
    "https://httpbin.org/status/500",    # для демонстрации ошибки со статусом 500
    "https://yandex.ru"                  # должно быть ОК, но будет редирект на другую страницу со статусом 302
]

async def run_job(job_id: UUID) -> None:
    # bind добавляет контекст (job_id) ко всем логам внутри этой задачи
    log = logger.bind(job_id=str(job_id), task="run_job")
    log.info("Background job started")

    async with AsyncSessionLocal() as session:
        job = await get_job(session, job_id)
        if job is None:
            log.warning(f"Job {job_id} not found in DB, nothing to do")
            return

        try:
            await set_status(session, job, JobStatus.PROCESSING)
            log.info("Set status -> PROCESSING")

            # получаем случайный URL
            url = choice(URLS)
            log.info(f"Requesting URL: {url}")

            # отправляем GET-запрос по указанному URL
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
            
            # если получаем статус на 2хх - задача завершилась с ошибкой
            response.raise_for_status()

            log.info(f"HTTP OK: status {response.status_code}")
            await set_status(
                session,
                job,
                JobStatus.DONE,
                finished_at=datetime.now(UTC),
            )

            log.success("Set status -> DONE")

        except Exception as e:
            await session.rollback()

            log.exception(f"Background job FAILED: {e}")

            await set_status(
                session,
                job,
                JobStatus.FAILED,
                finished_at=datetime.now(UTC),
                error=str(e),
            )