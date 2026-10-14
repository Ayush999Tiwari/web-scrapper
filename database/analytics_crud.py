from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from database.models import ScrapeJob

def get_start_date(range_str: str) -> datetime:
    # .replace(tzinfo=None) lagane se yeh PostgreSQL ke "TIMESTAMP WITHOUT TIME ZONE" se perfectly match karega
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if range_str == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_str == "7d":
        return now - timedelta(days=7)
    elif range_str == "30d":
        return now - timedelta(days=30)
    else:  # "all" ya default
        return now - timedelta(days=3650)  # 10 years as "all"


async def get_kpis(db: AsyncSession, range_str: str):
    start_date = get_start_date(range_str)
    
    q = select(
        func.count(ScrapeJob.id).label("total_crawls"),
        func.sum(case((ScrapeJob.status == "success", 1), else_=0)).label("success_count"),
        func.avg(ScrapeJob.crawl_time_seconds).label("avg_crawl_time"),
        func.sum(ScrapeJob.content_length).label("total_data_bytes"),
        func.count(func.distinct(ScrapeJob.domain)).label("unique_domains")
    ).where(ScrapeJob.created_at >= start_date)
    
    row = (await db.execute(q)).one()
    
    total = row.total_crawls or 0
    success = row.success_count or 0
    success_rate = round((success / total) * 100, 2) if total > 0 else 0.0
    
    return {
        "total_crawls": total,
        "success_rate": success_rate,
        "avg_crawl_time_seconds": round(row.avg_crawl_time or 0, 2),
        "total_data_bytes": row.total_data_bytes or 0,
        "unique_domains": row.unique_domains or 0,
    }


async def get_trends(db: AsyncSession, range_str: str):
    start_date = get_start_date(range_str)
    
    q = select(
        func.date_trunc("day", ScrapeJob.created_at).label("day"),
        func.count(ScrapeJob.id).label("count")
    ).where(
        ScrapeJob.created_at >= start_date
    ).group_by(
        "day"
    ).order_by("day")
    
    rows = (await db.execute(q)).all()
    
    return [{"date": row.day.strftime("%Y-%m-%d"), "count": row.count} for row in rows]


async def get_engine_stats(db: AsyncSession, range_str: str):
    start_date = get_start_date(range_str)
    
    q = select(
        ScrapeJob.engine_used,
        func.count(ScrapeJob.id).label("jobs"),
        func.sum(case((ScrapeJob.status == "success", 1), else_=0)).label("success_count"),
        func.avg(ScrapeJob.crawl_time_seconds).label("avg_time")
    ).where(
        ScrapeJob.created_at >= start_date
    ).group_by(
        ScrapeJob.engine_used
    )
    
    rows = (await db.execute(q)).all()
    
    result = []
    for row in rows:
        total = row.jobs or 0
        success = row.success_count or 0
        result.append({
            "engine": row.engine_used or "unknown",
            "jobs": total,
            "success_rate": round((success / total) * 100, 2) if total > 0 else 0.0,
            "avg_time_seconds": round(row.avg_time or 0, 2)
        })
    return result


async def get_top_domains(db: AsyncSession, range_str: str, limit: int = 10):
    start_date = get_start_date(range_str)
    
    q = select(
        ScrapeJob.domain,
        func.count(ScrapeJob.id).label("crawls"),
        func.sum(case((ScrapeJob.status == "success", 1), else_=0)).label("success_count"),
        func.avg(ScrapeJob.crawl_time_seconds).label("avg_time")
    ).where(
        ScrapeJob.created_at >= start_date,
        ScrapeJob.domain != None
    ).group_by(
        ScrapeJob.domain
    ).order_by(
        func.count(ScrapeJob.id).desc()
    ).limit(limit)
    
    rows = (await db.execute(q)).all()
    
    result = []
    for row in rows:
        total = row.crawls or 0
        success = row.success_count or 0
        result.append({
            "domain": row.domain,
            "crawls": total,
            "success_rate": round((success / total) * 100, 2) if total > 0 else 0.0,
            "avg_time_seconds": round(row.avg_time or 0, 2)
        })
    return result


async def get_error_breakdown(db: AsyncSession, range_str: str):
    start_date = get_start_date(range_str)
    
    # Total failed jobs in range (for percentage calculation)
    total_failed_q = select(func.count(ScrapeJob.id)).where(
        ScrapeJob.status == "failed",
        ScrapeJob.created_at >= start_date
    )
    total_failed = (await db.execute(total_failed_q)).scalar() or 0
    
    q = select(
        ScrapeJob.error_type,
        func.count(ScrapeJob.id).label("count")
    ).where(
        ScrapeJob.status == "failed",
        ScrapeJob.created_at >= start_date
    ).group_by(
        ScrapeJob.error_type
    ).order_by(
        func.count(ScrapeJob.id).desc()
    )
    
    rows = (await db.execute(q)).all()
    
    result = []
    for row in rows:
        result.append({
            "error_type": row.error_type or "none",
            "count": row.count,
            "percentage": round((row.count / total_failed) * 100, 2) if total_failed > 0 else 0.0
        })
    return result


async def get_content_stats(db: AsyncSession, range_str: str):
    start_date = get_start_date(range_str)
    
    q = select(
        func.count(ScrapeJob.id).label("pages_crawled"),
        func.sum(ScrapeJob.images_count).label("images"),
        func.sum(ScrapeJob.tables_count).label("tables"),
        func.sum(ScrapeJob.emails_found).label("emails"),
        func.sum(ScrapeJob.phones_found).label("phones"),
        func.sum(ScrapeJob.pdfs_count).label("pdfs"),
        func.sum(ScrapeJob.links_count).label("links")
    ).where(ScrapeJob.created_at >= start_date)
    
    row = (await db.execute(q)).one()
    
    return {
        "pages_crawled": row.pages_crawled or 0,
        "images_found": row.images or 0,
        "tables_extracted": row.tables or 0,
        "emails_found": row.emails or 0,
        "phones_found": row.phones or 0,
        "pdfs": row.pdfs or 0,
        "links_extracted": row.links or 0,
    }