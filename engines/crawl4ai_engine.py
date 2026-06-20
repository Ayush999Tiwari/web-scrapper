import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from schemas.response_schema import ScrapeResult, ScrapeStatus, EngineUsed
from utils.logger import get_logger

logger = get_logger(__name__)
async def scrape_with_crawl4ai(
    url: str,
    timeout: int = 30,
    min_content_length: int = 300,
    scroll_page: bool = False,
) -> ScrapeResult:
    logger.info(f"[Crawl4AI] Starting scrape: {url}")
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=timeout * 1000,
            wait_until="networkidle",
            scan_full_page=scroll_page,
            word_count_threshold=10,
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)  # type: ignore
        if not result.success:  # type: ignore
            logger.warning(f"[Crawl4AI] Crawl failed for {url} — {result.error_message}")  # type: ignore
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                engine_used=EngineUsed.CRAWL4AI,
                error_message=result.error_message or "Crawl4AI returned failure",  # type: ignore
            )
        metadata = {}
        if result.metadata:  # type: ignore
            for key, value in result.metadata.items():  # type: ignore
                if value is not None:
                    metadata[key] = value
        title = metadata.get("title") or metadata.get("og:title")
        links = []
        if result.links:  # type: ignore
            internal = result.links.get("internal", [])  # type: ignore
            external = result.links.get("external", [])  # type: ignore
            for link in internal + external:
                href = link.get("href", "")
                if href and href.startswith("http"):
                    links.append(href)
        content = result.markdown or result.extracted_content or ""  # type: ignore
        if not content or content.strip() == "":
            logger.warning(f"[Crawl4AI] Empty content for {url}")
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                engine_used=EngineUsed.CRAWL4AI,
                title=title,
                metadata=metadata,
                error_message="Empty content — page may be blocked or JS rendered",
            )
        content = content.strip()
        content_lower = content.lower()
        content_length = len(content)
        BAD_UI_PHRASES = [
            "skip to main content",
            "open menu",
            "get app",
            "home feed",
            "search with your voice",
        ]
        bad_hits = sum(1 for phrase in BAD_UI_PHRASES if phrase in content_lower)
        if bad_hits >= 2:
            logger.warning(f"[Crawl4AI] UI-heavy content detected for {url}")
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.PARTIAL,
                engine_used=EngineUsed.CRAWL4AI,
                title=title,
                content=content,
                metadata=metadata,
                links=links,
                content_length=content_length,
                error_message="UI/navigation-heavy content detected — likely JS page",
            )
        if content_length < min_content_length:
            logger.warning(f"[Crawl4AI] Content too short ({content_length} < {min_content_length}) for {url}")
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.PARTIAL,
                engine_used=EngineUsed.CRAWL4AI,
                title=title,
                content=content,
                metadata=metadata,
                links=links,
                content_length=content_length,
                error_message="Content too short — JS rendered page likely",
            )
        if not title and content_length < 500:
            logger.warning(f"[Crawl4AI] No title and very little content for {url}")
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.PARTIAL,
                engine_used=EngineUsed.CRAWL4AI,
                title=title,
                content=content,
                metadata=metadata,
                links=links,
                content_length=content_length,
                error_message="No title and very little content — possible boilerplate page",
            )
        BOILERPLATE_PHRASES = [
            "accept cookies",
            "we use cookies",
            "cookie policy",
            "enable javascript",
            "please enable javascript",
            "you need to enable javascript",
        ]
        if any(phrase in content_lower for phrase in BOILERPLATE_PHRASES) and content_length < 500:
            logger.warning(f"[Crawl4AI] Boilerplate/cookie content detected for {url}")
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.PARTIAL,
                engine_used=EngineUsed.CRAWL4AI,
                title=title,
                content=content,
                metadata=metadata,
                links=links,
                content_length=content_length,
                error_message="Boilerplate or cookie banner detected — JS rendered page likely",
            )

        logger.info(
            f"[Crawl4AI] Success — "
            f"content_length: {content_length} | "
            f"links: {len(links)} | "
            f"metadata keys: {list(metadata.keys())}"
        )

        return ScrapeResult(
            url=url,
            status=ScrapeStatus.SUCCESS,
            engine_used=EngineUsed.CRAWL4AI,
            title=title,
            content=content,
            metadata=metadata,
            links=links,
            content_length=content_length,
        )

    except asyncio.TimeoutError:
        logger.error(f"[Crawl4AI] Timeout for {url} after {timeout}s")
        return ScrapeResult(
            url=url,
            status=ScrapeStatus.FAILED,
            engine_used=EngineUsed.CRAWL4AI,
            error_message=f"Timeout after {timeout}s",
        )

    except Exception as e:
        logger.error(f"[Crawl4AI] Unexpected error for {url}: {e}")
        return ScrapeResult(
            url=url,
            status=ScrapeStatus.FAILED,
            engine_used=EngineUsed.CRAWL4AI,
            error_message=str(e),
        )