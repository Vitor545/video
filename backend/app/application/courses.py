from app.domain.entities import DownloadStatus
from app.infrastructure.repositories import (
    CourseRepository,
    VideoRepository,
    WatchHistoryRepository,
)


def _video_to_dict(video, history) -> dict:
    progress_seconds = history.progress_seconds if history else 0
    completed = history.completed if history else False
    return {
        "id": video.id,
        "title": video.title,
        "fcode": video.fcode,
        "module_name": video.module_name,
        "media_type": getattr(video, "media_type", "video"),
        "mime_type": getattr(video, "mime_type", None),
        "original_filename": getattr(video, "original_filename", None),
        "file_ext": getattr(video, "file_ext", None),
        "duration_seconds": video.duration_seconds,
        "order_index": video.order_index,
        "download_status": video.download_status,
        "file_size": video.file_size,
        "msg_id": video.msg_id,
        "progress_seconds": progress_seconds,
        "completed": completed,
    }


def _group_by_module(videos: list, history_map: dict) -> list[dict]:
    """Agrupa vídeos por módulo preservando a ordem original (order_index)."""
    modules: dict[str, dict] = {}
    module_order: list[str] = []
    for v in videos:
        if v.module_name not in modules:
            modules[v.module_name] = {
                "name": v.module_name,
                "videos": [],
                "total": 0,
                "done": 0,
                "completed": 0,
                "duration": 0,
            }
            module_order.append(v.module_name)
        m = modules[v.module_name]
        history = history_map.get(v.id)
        m["videos"].append(_video_to_dict(v, history))
        m["total"] += 1
        m["duration"] += v.duration_seconds
        if v.download_status == DownloadStatus.DONE:
            m["done"] += 1
        if history and history.completed:
            m["completed"] += 1
    return [modules[name] for name in module_order]


async def get_course_detail(
    course_id: int,
    user_id: int,
    course_repo: CourseRepository,
    video_repo: VideoRepository,
    history_repo: WatchHistoryRepository,
) -> dict | None:
    course = await course_repo.get_by_id(course_id)
    if not course:
        return None

    videos = await video_repo.list_by_course(course_id)
    history_map = await history_repo.get_for_videos(
        user_id=user_id,
        video_ids=[v.id for v in videos],
    )

    modules = _group_by_module(videos, history_map)
    downloaded = sum(1 for v in videos if v.download_status == DownloadStatus.DONE)
    completed = sum(1 for h in history_map.values() if h.completed)

    return {
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "telegram_channel": course.telegram_channel,
            "thumbnail_url": course.thumbnail_url,
            "total_videos": course.total_videos,
            "total_duration_seconds": course.total_duration_seconds,
        },
        "modules": modules,
        "total_videos": len(videos),
        "downloaded": downloaded,
        "completed": completed,
        "progress_pct": round(completed / len(videos) * 100) if videos else 0,
        "download_pct": round(downloaded / len(videos) * 100) if videos else 0,
    }
