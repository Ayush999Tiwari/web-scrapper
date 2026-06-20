import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
from schemas.response_schema import ScrapeResult, ScrapeStatus, EngineUsed
from utils.logger import get_logger
logger = get_logger(__name__)
def extract_metadata(html: str, base_url: str) -> tuple[dict, list[str]]:
    soup = BeautifulSoup(html, "lxml")
    metadata = {}
    links = []
    headings = []
    for tag in ["h1", "h2", "h3"]:
        for item in soup.find_all(tag):
            text = item.get_text(strip=True)
            if text:
                headings.append({
                    "tag": tag,
                    "text": text
                })
    metadata["headings"] = headings[:20]
    images = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if isinstance(src, str) and src.strip():
            images.append(urljoin(base_url, src))
    metadata["images"] = images[:20]
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        metadata["description"] = desc["content"]
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        metadata["og:title"] = og_title["content"]
    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        metadata["og:image"] = og_image["content"]
    for a in soup.find_all("a"):
        href = a.get("href")
        if isinstance(href, str) and href.strip():
            full_url = urljoin(base_url, href)
            if full_url.startswith("http"):
                links.append(full_url)
    links = list(dict.fromkeys(links))
    return metadata, links[:50]
async def scrape_with_playwright(
    url: str,
    timeout: int = 30,
    min_content_length: int = 300,
    scroll_page: bool = False,
    wait_for_selector: str | None = None,
) -> ScrapeResult:
    logger.info(f"[Playwright] Scraping: {url}")
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-IN",
            )
            page = await context.new_page()
            try:
                await page.goto(
                    url,
                    timeout=timeout * 1000,
                    wait_until="domcontentloaded"
                )
                try:
                    await page.wait_for_load_state(
                        "networkidle",
                        timeout=15000
                    )
                except PWTimeout:
                    logger.warning("[Playwright] networkidle timeout")
                await page.wait_for_timeout(4000)
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(
                            wait_for_selector,
                            timeout=10000
                        )
                    except PWTimeout:
                        logger.warning(
                            f"[Playwright] Selector not found: {wait_for_selector}"
                        )
                if scroll_page:
                    previous_height = 0
                    for _ in range(6):
                        current_height = await page.evaluate(
                            "document.body.scrollHeight"
                        )
                        if current_height == previous_height:
                            break
                        await page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)"
                        )
                        await asyncio.sleep(1.5)
                        previous_height = current_height
                html = await page.content()
                title = await page.title()
                logger.info(f"[Playwright] Raw HTML size: {len(html)}")
            finally:
                await browser.close()              
        metadata, links = extract_metadata(html, url)
        logger.info(
            f"[Playwright] Metadata keys: {list(metadata.keys())}"
        )
        logger.info(
            f"[Playwright] Links extracted: {len(links)}"
        )
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "path",
                "footer",
            ]
        ):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if len(line) < 2:
                continue
            lines.append(line)
        content = "\n".join(lines)
        content_length = len(content)
        logger.info(f"[Playwright] Cleaned text length: {content_length}")
        if not content:
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                engine_used=EngineUsed.PLAYWRIGHT,
                metadata=metadata,
                links=links,
                error_message="Empty content after render",
            )
        if content_length < min_content_length:
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.PARTIAL,
                engine_used=EngineUsed.PLAYWRIGHT,
                title=title,
                content=content,
                content_length=content_length,
                metadata=metadata,
                links=links,
                error_message="Low content after render",
            )
        return ScrapeResult(
            url=url,
            status=ScrapeStatus.SUCCESS,
            engine_used=EngineUsed.PLAYWRIGHT,
            title=title,
            content=content,
            content_length=content_length,
            metadata=metadata,
            links=links,
        )
    except Exception as e:
        logger.error(f"[Playwright] Error: {e}")
        return ScrapeResult(
            url=url,
            status=ScrapeStatus.FAILED,
            engine_used=EngineUsed.PLAYWRIGHT,
            error_message=str(e),
        )