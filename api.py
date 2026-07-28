import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from core.orchestrator import scrape_url
from database.db import get_db, init_db
from database.crud import save_scrape_result, get_all_scrapes, get_scrape_by_id
from utils.logger import get_logger
from core.exceptions import AppError
from routers.auth_router import router as auth_router
from routers.analytics_router import router as analytics_router
from core.url_validator import validate_url, URLValidationError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down application.")


app = FastAPI(
    title="Web Scraper Engine",
    description="Scrapes any URL using Crawl4AI with Playwright fallback",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Next.js abhi yahan chal raha hai
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(analytics_router)
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message},
    )
class ScrapeRequest(BaseModel):
    url: str
@app.get("/")
async def root():
    return {"message": "Web Scraper Engine is running"}
@app.post("/scrape")
async def scrape(request: ScrapeRequest, db: AsyncSession = Depends(get_db)):
    try: 
        validated_url = validate_url(request.url)
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))    
    logger.info(f"[API] Scrape request received for: {validated_url}")
    result = await scrape_url(validated_url)
    job = await save_scrape_result(db, result)
    return {
        "id": job.id,
        "url": result.url,
        "status": result.status,
        "engine_used": result.engine_used,
        "title": result.title,
        "content": result.content,
        "content_length": result.content_length,
        "metadata": result.metadata,
        "links": result.links,
        "error_message": result.error_message,
    }
@app.get("/scrape/{scrape_id}")
async def scrape_detail(scrape_id: int, db: AsyncSession = Depends(get_db)):
    job = await get_scrape_by_id(db, scrape_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scrape not found")
    return {
        "id": job.id,
        "url": job.url,
        "status": job.status,
        "engine_used": job.engine_used,
        "title": job.title,
        "content": job.content,
        "content_length": job.content_length,
        "metadata": job.metadata_,
        "links": job.links,
        "error_message": job.error_message,
        "created_at": job.created_at,
    }
@app.get("/history")
async def history(db: AsyncSession = Depends(get_db)):
    jobs = await get_all_scrapes(db)
    return [
        {
            "id": job.id,
            "url": job.url,
            "status": job.status,
            "engine_used": job.engine_used,
            "title": job.title,
            "content_length": job.content_length,
            "created_at": job.created_at,
        }
        for job in jobs
    ]
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)