from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import ScrapeJob
from schemas.response_schema import ScrapeResult
from utils.logger import get_logger

logger = get_logger(__name__)
async def save_scrape_result(db: AsyncSession, result: ScrapeResult) -> ScrapeJob:  # type: ignore
    job = ScrapeJob(
        url = result.url,
        status = result.status.value,
        engine_used = result.engine_used.value,
        title = result.title,
        content = result.content,
        content_length = result.content_length,
        metadata_ = result.metadata,
        error_message = result.error_message,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info(f"[DB] Saved — id: {job.id} | url: {result.url}")
    return job
async def get_scrape_by_url(db: AsyncSession, url: str):  # type: ignore
    result = await db.execute(
        select(ScrapeJob)
        .where(ScrapeJob.url == url)
        .order_by(ScrapeJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
async def get_all_scrapes(db: AsyncSession):  # type: ignore
    result = await db.execute(
        select(ScrapeJob).order_by(ScrapeJob.created_at.desc())
    )
    return result.scalars().all()