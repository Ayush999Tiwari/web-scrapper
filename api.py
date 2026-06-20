import asyncio
import sys
import uvicorn
from fastapi import FastAPI , Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from core.orchestrator import scrape_url
from database.db import get_db, init_db
from database.crud import save_scrape_result, get_all_scrapes
from utils.logger import get_logger
logger = get_logger(__name__)
app = FastAPI(
    title="Web Scraper Engine",
    description="Scrapes any URL using Crawl4AI with Playwright fallback",
    version="1.0.0"
)
class ScrapeRequest(BaseModel):
    url: str
@app.get("/")
async def root():
    return {"message": "Web Scraper Engine is running"}
@app.post("/scrape")
async def scrape(request: ScrapeRequest , db: AsyncSession = Depends(get_db)):
    logger.info(f"[API] Scrape request received for: {request.url}")
    result = await scrape_url(request.url)
    job = await save_scrape_result(db, result)
    return {
        "id" : job.id,
        "url" : result.url,
        "status" : result.status,
        "engine_used" : result.engine_used,
        "title" : result.title,
        "content" : result.content,
        "content_length": result.content_length,
        "metadata" : result.metadata,
        "links" : result.links,
        "error_message": result.error_message,
    }
@app.get("/history")
async def history(db: AsyncSession = Depends(get_db)):
    jobs = await get_all_scrapes(db)
    return [
        {
            "id" : job.id,
            "url" : job.url,
            "status" : job.status,
            "engine_used" : job.engine_used,
            "title" : job.title,
            "content_length": job.content_length,
            "created_at" : job.created_at,
        }
        for job in jobs
    ]
if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(app, host="0.0.0.0", port=8000)