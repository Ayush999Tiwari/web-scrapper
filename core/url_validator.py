from urllib.parse import urlparse
ALLOWED_SCHEMES = {"http" , "https"}
class URLValidationError(ValueError):
    pass
def validate_url(url : str ) -> str :
    if not isinstance(url, str) or not url.strip():
        raise URLValidationError("URL must be a non-empty string.")
    url = url.strip()
    if len(url) > 2048:
        raise URLValidationError("URL exceeds maximum allowed length of 2048 characters.")
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"Invalid scheme '{parsed.scheme}'. Only http and https are allowed."
        )
    if not parsed.netloc:
        raise URLValidationError("URL has no domain or host.")
    if "\x00" in url:
        raise URLValidationError("URL contains invalid null bytes.")
    return url
def is_valid_url(url: str) -> bool:
    try:
        validate_url(url)
        return True
    except URLValidationError:
        return False
