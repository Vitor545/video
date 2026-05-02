"""
Progress — orquestra leitura/gravação de progresso de aulas (WatchHistory).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import WatchHistoryRepository, VideoRepository


async def save_progress(
    user_id: int,
    video_id: int,
    progress_seconds: int,
    completed: bool,
    db: AsyncSession,
) -> dict:
    """
    Persiste progresso de uma aula. Marca como completed=True automaticamente
    se o usuário passou de 95% da duração, mesmo que o cliente não tenha
    sinalizado.
    """
    video = await VideoRepository(db).get_by_id(video_id)
    if video is None:
        raise ValueError(f"Vídeo {video_id} não encontrado")

    history_repo = WatchHistoryRepository(db)
    existing = await history_repo.get_for_video(user_id=user_id, video_id=video_id)

    if not completed and video.duration_seconds and video.duration_seconds > 0:
        if progress_seconds >= int(video.duration_seconds * 0.95):
            completed = True

    # Once a lesson is concluded, never demote it back to incomplete on subsequent
    # auto-saves — the player keeps emitting saves with completed=false while the
    # user re-watches or stays past the manual "Concluir aula" click.
    if existing and existing.completed:
        completed = True
        progress_seconds = max(int(progress_seconds), int(existing.progress_seconds or 0))

    await history_repo.upsert(
        user_id=user_id,
        video_id=video_id,
        progress_seconds=max(0, int(progress_seconds)),
        completed=completed,
    )

    return {
        "video_id": video_id,
        "progress_seconds": progress_seconds,
        "completed": completed,
    }


async def get_progress(user_id: int, video_id: int, db: AsyncSession) -> dict:
    """Retorna progresso atual do usuário no vídeo, ou zeros se nunca assistiu."""
    repo = WatchHistoryRepository(db)
    entry = await repo.get_for_video(user_id=user_id, video_id=video_id)
    if entry is None:
        return {"video_id": video_id, "progress_seconds": 0, "completed": False}
    return {
        "video_id": video_id,
        "progress_seconds": entry.progress_seconds,
        "completed": entry.completed,
    }
