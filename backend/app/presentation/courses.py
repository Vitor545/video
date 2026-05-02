from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.courses import get_course_detail
from app.database import get_db
from app.infrastructure.repositories import (
    CourseRepository,
    VideoRepository,
    WatchHistoryRepository,
)
from app.presentation.auth import get_current_user_id

router = APIRouter(prefix="/courses", tags=["courses"])


class CourseIn(BaseModel):
    title: str
    telegram_channel: str
    description: str | None = None


@router.get("/")
async def list_courses(db: AsyncSession = Depends(get_db)):
    return await CourseRepository(db).list_all()


@router.post("/", status_code=201)
async def create_course(data: CourseIn, db: AsyncSession = Depends(get_db)):
    return await CourseRepository(db).create(**data.model_dump())


@router.get("/{course_id}")
async def get_course(
    course_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    detail = await get_course_detail(
        course_id=course_id,
        user_id=user_id,
        course_repo=CourseRepository(db),
        video_repo=VideoRepository(db),
        history_repo=WatchHistoryRepository(db),
    )
    if not detail:
        raise HTTPException(404, "Curso não encontrado")
    return detail


@router.get("/{course_id}/videos")
async def list_course_videos(
    course_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os vídeos do curso com status de download e progresso do usuário."""
    course = await CourseRepository(db).get_by_id(course_id)
    if not course:
        raise HTTPException(404, "Curso não encontrado")

    videos = await VideoRepository(db).list_by_course(course_id)
    history_map = await WatchHistoryRepository(db).get_for_videos(
        user_id=user_id,
        video_ids=[v.id for v in videos],
    )
    return [
        {
            "id": v.id,
            "module_name": v.module_name,
            "title": v.title,
            "fcode": v.fcode,
            "media_type": getattr(v, "media_type", "video"),
            "mime_type": getattr(v, "mime_type", None),
            "original_filename": getattr(v, "original_filename", None),
            "file_ext": getattr(v, "file_ext", None),
            "duration_seconds": v.duration_seconds,
            "order_index": v.order_index,
            "download_status": v.download_status,
            "file_size": v.file_size,
            "msg_id": v.msg_id,
            "progress_seconds": (
                history_map[v.id].progress_seconds if v.id in history_map else 0
            ),
            "completed": (
                history_map[v.id].completed if v.id in history_map else False
            ),
        }
        for v in videos
    ]
