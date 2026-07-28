from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import ScrapeJob
from schemas.response_schema import ScrapeResult
from utils.logger import get_logger

logger = get_logger(__name__)

async def save_scrape_result(db: AsyncSession, result: ScrapeResult) -> ScrapeJob:  # type: ignore
    job = ScrapeJob(
        url=result.url,
        status=result.status.value,
        engine_used=result.engine_used.value,
        title=result.title,
        content=result.content,
        content_length=result.content_length,
        metadata_=result.metadata,
        links=result.links,
        error_message=result.error_message,
        crawl_time_seconds=result.crawl_time_seconds,
        images_count=result.images_count,
        tables_count=result.tables_count,
        emails_found=result.emails_found,
        phones_found=result.phones_found,
        error_type=result.error_type,
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

async def get_scrape_by_id(db: AsyncSession, scrape_id: int):  # type: ignore
    result = await db.execute(
        select(ScrapeJob).where(ScrapeJob.id == scrape_id)
    )
    return result.scalar_one_or_none()