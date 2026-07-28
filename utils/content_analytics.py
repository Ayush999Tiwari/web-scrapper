import re

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'\+?\d[\d\-\s()]{8,}\d')
MD_IMAGE_RE = re.compile(r'!\[.*?\]\(.*?\)')
MD_TABLE_SEP_RE = re.compile(r'^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$', re.MULTILINE)


def count_images(raw_content: str) -> int:
    """Count markdown image syntax. Must run on RAW content, before clean_content() strips it."""
    if not raw_content:
        return 0
    return len(MD_IMAGE_RE.findall(raw_content))


def count_tables(raw_content: str) -> int:
    """Count markdown tables by detecting header-separator rows like | --- | --- |."""
    if not raw_content:
        return 0
    return len(MD_TABLE_SEP_RE.findall(raw_content))


def count_emails(content: str) -> int:
    if not content:
        return 0
    return len(set(EMAIL_RE.findall(content)))


def count_phones(content: str) -> int:
    if not content:
        return 0
    return len(set(PHONE_RE.findall(content)))


def count_pdfs(links: list[str]) -> int:
    if not links:
        return 0
    return sum(1 for l in links if l.lower().split("?")[0].endswith(".pdf"))


def categorize_error(error_message: str | None, status_code: int | None = None) -> str:
    """Bucket error_message into a fixed set of categories for the Error Analysis chart."""
    msg = (error_message or "").lower()
    if status_code == 403 or "forbidden" in msg:
        return "403_forbidden"
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "captcha" in msg:
        return "captcha"
    if status_code == 404 or "not found" in msg:
        return "404"
    if "javascript" in msg or "js rendered" in msg or "js render" in msg:
        return "js_rendering"
    if not msg:
        return "none"
    return "other"