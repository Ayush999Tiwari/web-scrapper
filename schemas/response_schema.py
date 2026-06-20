
from enum import Enum
from pydantic import BaseModel
class EngineUsed(str, Enum):
    CRAWL4AI = "crawl4ai"
    PLAYWRIGHT = "playwright"
    NONE = "none"
class ScrapeStatus(str, Enum):
    SUCCESS = "success"  
    PARTIAL = "partial"  
    FAILED  = "failed"   
class ScrapeResult(BaseModel):
    url : str
    status : ScrapeStatus
    engine_used : EngineUsed
    title : str | None = None
    content : str | None = None  
    metadata : dict = {}
    links : list[str] = []
    content_length : int = 0
    error_message : str | None = None

    def is_usable(self) -> bool:
        return (
            self.status in (ScrapeStatus.SUCCESS, ScrapeStatus.PARTIAL)
            and bool(self.content)
            and self.content_length > 0
        )

    def to_dict(self) -> dict:
        """Convert result to plain dictionary."""
        return self.model_dump()
