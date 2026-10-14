from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from database import analytics_crud as crud

router = APIRouter(prefix="/analytics", tags=["analytics"])

RangeParam = Query("30d", pattern="^(today|7d|30d|all)$")

@router.get("/kpis")
async def kpis(range: str = RangeParam, db: AsyncSession = Depends(get_db)):
    return await crud.get_kpis(db, range)

@router.get("/trends")
async def trends(range: str = RangeParam, db: AsyncSession = Depends(get_db)):
    return await crud.get_trends(db, range)

@router.get("/engines")
async def engines(range: str = RangeParam, db: AsyncSession = Depends(get_db)):
    return await crud.get_engine_stats(db, range)

@router.get("/top-domains")
async def top_domains(range: str = RangeParam, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_top_domains(db, range, limit)

@router.get("/errors")
async def errors(range: str = RangeParam, db: AsyncSession = Depends(get_db)):
    return await crud.get_error_breakdown(db, range)

@router.get("/content-stats")
async def content_stats(range: str = RangeParam, db: AsyncSession = Depends(get_db)):
    return await crud.get_content_stats(db, range)