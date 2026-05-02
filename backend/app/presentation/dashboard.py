"""
Dashboard router — endpoints agregados para o painel principal do usuário.
Todos exigem autenticação (Bearer JWT).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import dashboard as dashboard_svc
from app.database import get_db
from app.presentation.auth import get_current_user_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def stats(
    course_id: int | None = Query(None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_stats(user_id, db, course_id=course_id)


@router.get("/weekly")
async def weekly(
    weeks: int = Query(8, ge=1, le=52),
    course_id: int | None = Query(None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_weekly(user_id, db, weeks=weeks, course_id=course_id)


@router.get("/streak")
async def streak(
    course_id: int | None = Query(None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_streak(user_id, db, course_id=course_id)


@router.get("/hourly")
async def hourly(
    course_id: int | None = Query(None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_hourly(user_id, db, course_id=course_id)


@router.get("/recent")
async def recent(
    limit: int = Query(10, ge=1, le=50),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_recent(user_id, db, limit=limit)


@router.get("/modules")
async def modules(
    top: int = Query(5, ge=1, le=20),
    course_id: int | None = Query(None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_modules(user_id, db, top=top, course_id=course_id)


@router.get("/my-courses")
async def my_courses(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_svc.get_my_courses(user_id, db)
