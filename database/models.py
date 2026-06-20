from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False)
    status = Column(String(50), nullable=False)
    engine_used = Column(String(50), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    content_length = Column(Integer, default=0)
    metadata_ = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())