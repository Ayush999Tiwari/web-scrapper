import asyncio
import time
from core.url_validator import validate_url, URLValidationError
from core.scoring import compute_quality_score
from engines.crawl4ai_engine import scrape_with_crawl4ai
from engines.playwright_engine import scrape_with_playwright
from schemas.response_schema import ScrapeResult, ScrapeStatus, EngineUsed
from utils.content_cleaner import clean_content
from utils.logger import get_logger
logger = get_logger(__name__)
UI_PHRASES = [
    "skip to main content",
    "skip navigation",
    "log in",
    "sign in",
    "sign up",
    "menu",
    "home feed",
    "get app",
    "search with your voice",
    "enable javascript",
    "please enable javascript",
]
MAX_RETRIES = 3
RETRY_DELAY = 2
def _compute_score(result: ScrapeResult) -> float:
    content = result.content or ""
    title = result.title
    lower = content.lower()
    bad_hits = sum(1 for p in UI_PHRASES if p in lower)
    return compute_quality_score(content, title, bad_hits)
async def _run_crawl4ai_with_retry(url: str) -> ScrapeResult:
    result = None
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"[Orchestrator] Crawl4AI attempt {attempt}/{MAX_RETRIES} for: {url}")
        result = await scrape_with_crawl4ai(url)
        score = _compute_score(result)
        logger.info(f"[Orchestrator] Crawl4AI attempt {attempt} score: {score}")
        if score >= 75 and result.status != ScrapeStatus.FAILED:
            return result
        if attempt < MAX_RETRIES:
            logger.warning(f"[Orchestrator] Attempt {attempt} failed — retrying in {RETRY_DELAY}s")
            await asyncio.sleep(RETRY_DELAY)
    return result # type: ignore
async def scrape_url(url: str) -> ScrapeResult:
    start_time = time.perf_counter()
    logger.info(f"[Orchestrator] -> START — url: {url}")    
    try:
        url = validate_url(url)
    except URLValidationError as e:
        logger.error(f"[Orchestrator] Invalid URL: {url} — {e}")
        return ScrapeResult(
            url=url,
            status=ScrapeStatus.FAILED,
            engine_used=EngineUsed.NONE,
            error_message=f"Invalid URL: {e}"
        )
    result = await _run_crawl4ai_with_retry(url)
    score  = _compute_score(result)
    if score >= 75 and result.status != ScrapeStatus.FAILED:
        result.engine_used = EngineUsed.CRAWL4AI
        result.content = clean_content(result.content or "")
        result.content_length = len(result.content)
        elapsed = round(time.perf_counter() - start_time, 2)
        logger.info(
            f"[Orchestrator]  END — "
            f"engine: crawl4ai | "
            f"status: {result.status} | "
            f"length: {result.content_length} | "
            f"time: {elapsed}s"
        )
        return result
    logger.warning(
        f"[Orchestrator] All Crawl4AI attempts failed — "
        f"falling back to Playwright"
    )
    fallback_result = await scrape_with_playwright(url)
    fallback_result.engine_used = EngineUsed.PLAYWRIGHT
    fallback_result.content = clean_content(fallback_result.content or "")
    fallback_result.content_length = len(fallback_result.content)
    elapsed = round(time.perf_counter() - start_time, 2)
    if fallback_result.is_usable():
        logger.info(f"[Orchestrator] Playwright succeeded for: {url}")
    else:
        logger.error(f"[Orchestrator] Both engines failed for: {url}")
    logger.info(
        f"[Orchestrator]  END — "
        f"engine: playwright | "
        f"status: {fallback_result.status} | "
        f"length: {fallback_result.content_length} | "
        f"time: {elapsed}s"
    )
    return fallback_result
   