import re
from utils.logger import get_logger

logger = get_logger(__name__)
JUNK_PHRASES = [
    "skip to main content",
    "skip navigation",
    "sign in",
    "sign up",
    "log in",
    "log out",
    "register",
    "home feed",
    "get app",
    "search with your voice",
    "enable javascript",
    "please enable javascript",
    "accept cookies",
    "we use cookies",
    "cookie policy",
    "privacy policy",
    "terms of service",
    "all rights reserved",
    "back to top",
    "follow us",
    "subscribe",
    "newsletter",
    "copyright",
    "share this",
    "click here",
    "advertisement",
    "make money with us",
    "let us help you",
    "get to know us",
    "connect with us",
    "conditions of use",
    "site footer",
]


def clean_content(content: str) -> str:
    if not content or content.strip() == "":
        logger.warning("[Cleaner] Empty content received")
        return ""
    logger.debug(f"[Cleaner] Input length: {len(content)}")
    content = re.sub(r'([a-z\.\!\?])([A-Z])', r'\1\n\2', content)
    content = content.replace('\xa0', ' ')
    content = content.replace('\u200b', '')
    content = content.replace('\u200c', '')
    content = content.replace('\u200d', '')
    content = content.replace('\r', '\n')
    content = content.replace('\t', ' ')

    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    content = re.sub(r'\[\s*\]\([^\)]*\)', '', content)
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    content = re.sub(r'\|+', ' ', content)
    content = re.sub(r'http[s]?://\S+', '', content)
    content = re.sub(r'#{1,6}\s', '', content)
    content = re.sub(r'\*{1,3}', '', content)
    content = re.sub(r'~~.*?~~', '', content)
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
    content = re.sub(r'-{3,}', '', content)
    lines = content.splitlines()
    cleaned_lines = []
    seen_lines = set()
    for line in lines:
        line = line.strip()
        line_lower = line.lower()

        if not line:
            continue
        if any(phrase in line_lower for phrase in JUNK_PHRASES):
            continue
        if len(line.split()) < 2:
            continue
        if line_lower in seen_lines:
            continue
        seen_lines.add(line_lower)
        cleaned_lines.append(line)
    content = "\n".join(cleaned_lines)
    content = re.sub(r' {2,}', ' ', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    logger.info(f"[Cleaner] Done — output length: {len(content)}")
    return content.strip()