from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.infrastructure.repositories import VideoRepository, DownloadJobRepository, CourseRepository
from app.infrastructure.storage import delete as storage_delete
from app.application.downloads import queue_download, get_queue_status, cancel_job, cancel_all
from app.database import AsyncSessionLocal

router = APIRouter(prefix="/downloads", tags=["downloads"])


class BatchDownloadIn(BaseModel):
    video_ids: List[int]

@router.post("/batch", status_code=202)
async def enqueue_batch(data: BatchDownloadIn, db: AsyncSession = Depends(get_db)):
    job_repo = DownloadJobRepository(db)
    video_repo = VideoRepository(db)
    
    enqueued = []
    for vid in data.video_ids:
        video = await video_repo.get_by_id(vid)
        if not video or video.storage_path:
            continue
            
        job = await job_repo.get_by_video(vid)
        if not job or job.status.value in ("failed", "done"):
            job = await job_repo.create(vid)
            await queue_download(job.id)
            enqueued.append(vid)
            
    return {"queued_count": len(enqueued), "video_ids": enqueued}


@router.post("/jobs/{job_id}/retry", status_code=202)
async def retry_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job_repo = DownloadJobRepository(db)
    job = await job_repo.get(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    await queue_download(job_id)
    return {"status": "retrying", "job_id": job_id}


@router.delete("/jobs/{job_id}", status_code=200)
async def cancel_one(job_id: int):
    cancelled = await cancel_job(job_id, AsyncSessionLocal)
    if not cancelled:
        raise HTTPException(404, "Job não encontrado")
    return {"status": "cancelled", "job_id": job_id}


@router.post("/cancel-all", status_code=200)
async def cancel_all_jobs():
    count = await cancel_all(AsyncSessionLocal)
    return {"status": "ok", "cancelled_count": count}


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    q_status = await get_queue_status()
    # Pega os jobs que ainda não começaram ou falharam etc da base para listar
    jobs = await DownloadJobRepository(db).list_all_with_videos()
    
    return {
        "worker": q_status,
        "jobs": [
            {
                "id": j.id,
                "video_id": j.video_id,
                "status": j.status,
                "attempts": j.attempts,
                "error": j.error_message,
                "video_title": j.video.title if j.video else None,
                "fcode": j.video.fcode if j.video else None,
                "duration_seconds": j.video.duration_seconds if j.video else None,
                "course_id": j.video.course_id if j.video else None,
                "course_title": j.video.course.title if j.video and j.video.course else None,
                "module_name": j.video.module_name if j.video else None,
                "file_size": j.video.file_size if j.video else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            }
            for j in jobs
        ]
    }


@router.delete("/videos/{video_id}/storage", status_code=204)
async def delete_video_storage(video_id: int, db: AsyncSession = Depends(get_db)):
    from app.domain.entities import DownloadStatus
    video_repo = VideoRepository(db)
    job_repo = DownloadJobRepository(db)

    video = await video_repo.get_by_id(video_id)
    if not video:
        raise HTTPException(404, "Vídeo não encontrado")

    if video.storage_path:
        storage_delete(video.storage_path)

    await video_repo.update_storage_path(video_id, None)
    await video_repo.update_status(video_id, DownloadStatus.PENDING)

    job = await job_repo.get_by_video(video_id)
    if job:
        await db.delete(job)
        await db.commit()


@router.delete("/courses/{course_id}/storage", status_code=204)
async def delete_course_storage(course_id: int, db: AsyncSession = Depends(get_db)):
    from app.domain.entities import DownloadStatus
    video_repo = VideoRepository(db)
    job_repo = DownloadJobRepository(db)
    videos = await video_repo.list_by_course(course_id)

    for v in videos:
        if v.storage_path:
            storage_delete(v.storage_path)
        await video_repo.update_storage_path(v.id, None)
        await video_repo.update_status(v.id, DownloadStatus.PENDING)
        job = await job_repo.get_by_video(v.id)
        if job:
            await db.delete(job)

    await db.commit()

