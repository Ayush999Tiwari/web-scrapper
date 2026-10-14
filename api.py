
import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

import uvicorn
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Depends,
    Request,
    HTTPException,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.orchestrator import scrape_url
from core.url_validator import validate_url, URLValidationError
from core.exceptions import AppError

from database.db import get_db, init_db
from database.crud import (
    save_scrape_result,
    get_all_scrapes,
    get_scrape_by_id,
)

from utils.logger import get_logger

from routers.auth_router import router as auth_router
from routers.analytics_router import router as analytics_router
from routers.chat_router import router as chat_router

from services.rag_service import index_scrape


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized successfully.")

    yield

    logger.info("Shutting down application.")


app = FastAPI(
    title="Web Scraper Engine",
    description=(
        "Scrapes websites using Crawl4AI with Playwright fallback "
        "and provides RAG-based chat over scraped website content."
    ),
    version="1.1.0",
    lifespan=lifespan,
)


# Session middleware required by Authlib for Google OAuth state.
session_secret = os.getenv("SESSION_SECRET")

if not session_secret:
    raise RuntimeError(
        "SESSION_SECRET is missing. Add a strong random secret "
        "to your backend .env file."
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    https_only=(
        os.getenv("COOKIE_HTTPS_ONLY", "false").lower() == "true"
    ),
    same_site="lax",
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Existing routers
app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(chat_router)


@app.exception_handler(AppError)
async def app_error_handler(
    request: Request,
    exc: AppError,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
        },
    )


class ScrapeRequest(BaseModel):
    url: str


def index_scrape_safely(
    scrape_id: int,
    url: str,
    title: str | None,
    content: str,
):
    """
    Index saved website content without breaking scraping
    if embedding generation or vector storage fails.
    """
    try:
        chunk_count = index_scrape(
            scrape_id,
            url,
            title,
            content,
        )

        logger.info(
            "[RAG] Indexed scrape_id=%s, chunks=%s",
            scrape_id,
            chunk_count,
        )

    except Exception:
        logger.exception(
            "[RAG] Background indexing failed for scrape_id=%s",
            scrape_id,
        )


@app.get("/")
async def root():
    return {
        "message": "Web Scraper Engine is running",
        "chatbot": "RAG chatbot enabled",
        "docs": "/docs",
    }


@app.post("/scrape")
async def scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        validated_url = validate_url(request.url)

    except URLValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    logger.info(
        "[API] Scrape request received for: %s",
        validated_url,
    )

    # Existing scraper logic remains unchanged.
    result = await scrape_url(validated_url)

    # Save the original result to PostgreSQL first.
    job = await save_scrape_result(db, result)

    # Index successful, non-empty content in the background.
    if (
        job.status.lower() in {"success", "completed"}
        and job.content
        and job.content.strip()
    ):
        background_tasks.add_task(
            index_scrape_safely,
            job.id,
            job.url,
            job.title,
            job.content,
        )

    # Preserve the existing response structure.
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
async def scrape_detail(
    scrape_id: int,
    db: AsyncSession = Depends(get_db),
):
    job = await get_scrape_by_id(db, scrape_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Scrape not found",
        )

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
async def history(
    db: AsyncSession = Depends(get_db),
):
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
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
