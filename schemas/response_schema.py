
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
    crawl_time_seconds: float = 0.0 
    images_count: int = 0                  
    tables_count: int = 0                 
    emails_found: int = 0                 
    phones_found: int = 0             
    links_count: int = 0     
    pdfs_count: int = 0     
    error_type: str | None = None

    def is_usable(self) -> bool:
        return (
            self.status in (ScrapeStatus.SUCCESS, ScrapeStatus.PARTIAL)
            and bool(self.content)
            and self.content_length > 0
        )

    def to_dict(self) -> dict:
        """Convert result to plain dictionary."""
        return self.model_dump()
