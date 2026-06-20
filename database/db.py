from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
DATABASE_URL = "postgresql+asyncpg://postgres:Postgress123@localhost:5432/scraper_db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker( 
    bind=engine, # type: ignore
    class_=AsyncSession,
    expire_on_commit=False
) # type: ignore
Base = declarative_base()
async def get_db():
    async with AsyncSessionLocal() as session: # type: ignore
        yield session
async def init_db():
    async with engine.begin() as conn:
        from database.models import ScrapeJob , Base
        await conn.run_sync(Base.metadata.create_all)