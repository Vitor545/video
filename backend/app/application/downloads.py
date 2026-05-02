import asyncio
import logging
import os
from pathlib import Path
from datetime import datetime, UTC
from typing import Callable
from asyncio.subprocess import DEVNULL, PIPE

from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories import DownloadJobRepository, VideoRepository, TelegramConfigRepository
from app.infrastructure.telegram import connect, download_video
from app.infrastructure.storage import upload
from app.domain.entities import DownloadStatus
from app.config import settings

logger = logging.getLogger(__name__)

# Max concurrent downloads (compressão é CPU-bound, manter baixo evita travar a fila)
MAX_CONCURRENT_DOWNLOADS = 2
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
_queue: asyncio.Queue[int] = asyncio.Queue()
_active_downloads: dict[int, dict] = {}  # { job_id: { progress_bytes, total_bytes } }
_active_tasks: dict[int, asyncio.Task] = {}  # { job_id: Task } — para poder cancelar
_queued_ids: set[int] = set()  # job_ids enfileirados (pra cancelar antes de iniciar)

async def _probe_duration_seconds(input_path: Path) -> int | None:
    try:
        if not input_path.exists():
            return None

        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        raw = stdout.decode(errors="ignore").strip()
        if not raw:
            return None
        seconds = float(raw)
        if seconds <= 0:
            return None
        return max(1, int(seconds + 0.5))
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning("ffprobe duration falhou: %s", e)
        return None

async def _compress_mp4(input_path: Path) -> Path:
    try:
        if not input_path.exists():
            return input_path

        compress_enabled = bool(getattr(settings, "video_compress_enabled", True))
        codec = getattr(settings, "video_compress_codec", "libx264") or "libx264"
        crf = int(getattr(settings, "video_compress_crf", 28) or 28)
        preset = getattr(settings, "video_compress_preset", "medium") or "medium"
        audio_bitrate = getattr(settings, "video_audio_bitrate", "96k") or "96k"

        output_path = input_path.with_suffix(".compressed.mp4")
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass

        if compress_enabled:
            ffmpeg_args = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-c:v", codec,
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", audio_bitrate,
                "-movflags", "+faststart",
                str(output_path),
            ]
        else:
            if input_path.suffix.lower() != ".mp4":
                return input_path
            ffmpeg_args = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-c", "copy",
                "-movflags", "+faststart",
                str(output_path),
            ]

        original_size = input_path.stat().st_size
        proc = await asyncio.create_subprocess_exec(
            *ffmpeg_args,
            stdout=DEVNULL,
            stderr=PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            new_size = output_path.stat().st_size
            if compress_enabled and new_size >= original_size:
                logger.info(
                    "Compressão não reduziu tamanho (orig=%d, novo=%d) — mantendo original",
                    original_size, new_size,
                )
                try:
                    output_path.unlink()
                except OSError:
                    pass
                return input_path
            logger.info(
                "Compressão concluída: %d -> %d bytes (%.1f%% do original)",
                original_size, new_size, (new_size / original_size * 100) if original_size else 0,
            )
            return output_path

        if stderr:
            logger.warning("ffmpeg falhou (rc=%s): %s", proc.returncode, stderr.decode(errors="ignore")[:500])
        try:
            if output_path.exists():
                output_path.unlink()
        except OSError:
            pass
        return input_path
    except FileNotFoundError:
        return input_path
    except Exception as e:
        logger.warning("ffmpeg compressão falhou: %s", e)
        return input_path

async def get_queue_status() -> dict:
    return {
        "queued": _queue.qsize(),
        "active": _active_downloads,
    }

async def queue_download(job_id: int):
    _queued_ids.add(job_id)
    await _queue.put(job_id)


def _cleanup_temp_files_for_video(video_id: int | None) -> None:
    """Remove arquivos parciais em temp_downloads/ que correspondam ao vídeo cancelado."""
    if video_id is None:
        return
    temp_dir = Path("temp_downloads")
    if not temp_dir.exists():
        return
    pattern_prefix = f"{video_id}."
    for p in temp_dir.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith(pattern_prefix) or f"_{video_id}." in p.name:
            try:
                p.unlink()
                logger.info("Removido arquivo parcial: %s", p)
            except OSError:
                pass


async def cancel_job(job_id: int, db_factory: Callable) -> bool:
    """Cancela um job — em andamento, enfileirado ou pending no DB.

    Retorna True se algo foi feito. Cancela a task asyncio (se ativa),
    remove arquivos parciais e apaga o job do DB.
    """
    cancelled_something = False
    video_id: int | None = None

    async with db_factory() as db:
        job_repo = DownloadJobRepository(db)
        job = await job_repo.get(job_id)
        if job:
            video_id = job.video_id

    task = _active_tasks.pop(job_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=10)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        cancelled_something = True

    _queued_ids.discard(job_id)
    _active_downloads.pop(job_id, None)
    _cleanup_temp_files_for_video(video_id)

    async with db_factory() as db:
        job_repo = DownloadJobRepository(db)
        job = await job_repo.get(job_id)
        if job:
            await db.delete(job)
            await db.commit()
            cancelled_something = True

    return cancelled_something


async def cancel_all(db_factory: Callable) -> int:
    """Cancela TODOS os jobs em andamento, enfileirados e pendentes."""
    job_ids = set(_active_tasks.keys()) | set(_queued_ids)

    async with db_factory() as db:
        job_repo = DownloadJobRepository(db)
        pending = await job_repo.list_pending_and_retry()
        job_ids.update(j.id for j in pending)
        # Inclui também os DOWNLOADING que possam estar fora do _active_tasks
        # (ex.: backend reiniciado). Lista tudo que não é done/failed.
        all_jobs = await job_repo.list_all_with_videos()
        for j in all_jobs:
            if j.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.RETRY_PENDING):
                job_ids.add(j.id)

    cancelled = 0
    for jid in job_ids:
        try:
            if await cancel_job(jid, db_factory):
                cancelled += 1
        except Exception as e:
            logger.warning("Falha ao cancelar job %s: %s", jid, e)

    # Drena qualquer resto da fila
    while not _queue.empty():
        try:
            _queue.get_nowait()
            _queue.task_done()
        except asyncio.QueueEmpty:
            break
    _queued_ids.clear()

    return cancelled

async def process_job(job_id: int, db_factory: Callable):
    _queued_ids.discard(job_id)
    async with _semaphore:
        async with db_factory() as db:
            job_repo = DownloadJobRepository(db)
            video_repo = VideoRepository(db)
            job = await job_repo.get(job_id)

            if not job or job.status == DownloadStatus.DONE:
                return

            # Check if it's retry pending and not ready
            if job.status == DownloadStatus.RETRY_PENDING and job.next_retry_at:
                if datetime.now(UTC).replace(tzinfo=None) < job.next_retry_at:
                    # Put back in queue after delay (simple approach)
                    delay = (job.next_retry_at - datetime.now(UTC).replace(tzinfo=None)).total_seconds()
                    asyncio.create_task(_delayed_requeue(job_id, max(1, delay)))
                    return

            await job_repo.set_downloading(job_id)
            video = await video_repo.get_by_id(job.video_id)
            if not video:
                await job_repo.set_failed(job_id, "Video not found")
                return

            _active_downloads[job_id] = {"progress_bytes": 0, "total_bytes": video.file_size or 0}

            try:
                # 1. Busca credenciais Telegram da integração vinculada ao curso
                tg_repo = TelegramConfigRepository(db)
                all_configs = await tg_repo.list_all()
                logger.info(f"[job={job_id}] video.course_id={video.course_id}, configs={[(c.id, c.course_id) for c in all_configs]}")
                tg_configs = [c for c in all_configs if c.course_id == video.course_id]
                if not tg_configs:
                    # fallback: usa qualquer config ativa
                    tg_configs = [c for c in all_configs if c.is_active]
                if not tg_configs:
                    raise RuntimeError(f"Nenhuma integração Telegram disponível para o curso {video.course_id}")
                tg = tg_configs[0]
                session_path = settings.telegram_session_path
                logger.info(f"[job={job_id}] Obtendo cliente Telegram (integration={tg.id})...")
                client = await connect(int(tg.api_id), tg.api_hash, session_path)

                # 2. Download
                def progress_cb(current, total):
                    _active_downloads[job_id]["progress_bytes"] = current
                    _active_downloads[job_id]["total_bytes"] = total

                temp_dir = Path("temp_downloads")
                temp_dir.mkdir(exist_ok=True)
                
                logger.info(f"[job={job_id}] Downloading msg_id={video.msg_id}...")
                local_path = await download_video(
                    client, 
                    video.msg_id, 
                    temp_dir, 
                    video.source_name, # channel name is source_name
                    progress_callback=progress_cb
                )

                source_path = Path(local_path)
                media_type = (getattr(video, "media_type", "video") or "video").lower()
                optimized_path = source_path if media_type != "video" else await _compress_mp4(source_path)
                actual_size = optimized_path.stat().st_size if optimized_path.exists() else None
                duration_seconds = await _probe_duration_seconds(optimized_path) if media_type == "video" else None

                # 3. Move arquivo otimizado para o storage final
                logger.info(f"[job={job_id}] Moving to storage...")
                ext = (
                    getattr(video, "file_ext", None)
                    or optimized_path.suffix
                    or (".mp4" if media_type == "video" else "")
                )
                if ext and not str(ext).startswith("."):
                    ext = f".{ext}"
                prefix = "video" if media_type == "video" else "file"
                storage_key = f"courses/{video.course_id}/modules/{video.module_name}/{prefix}_{video.id}{ext}"
                storage_key = storage_key.replace(" ", "_")

                uploaded_key = await asyncio.get_event_loop().run_in_executor(
                    None, upload, optimized_path, storage_key
                )

                # 4. Update DB
                await video_repo.update_storage_path(video.id, uploaded_key, file_size=actual_size)
                if duration_seconds and (not video.duration_seconds or video.duration_seconds <= 0):
                    await video_repo.update_duration_seconds(video.id, duration_seconds)
                await video_repo.update_status(video.id, DownloadStatus.DONE)
                await job_repo.set_done(job_id)
                logger.info(f"[job={job_id}] Finished successfully.")

                if optimized_path != source_path and source_path.exists():
                    try:
                        os.remove(str(source_path))
                    except OSError:
                        pass

            except asyncio.CancelledError:
                logger.info(f"[job={job_id}] Cancelado pelo usuário")
                _cleanup_temp_files_for_video(video.id if video else None)
                raise

            except Exception as e:
                logger.error(f"[job={job_id}] Failed: {e}")
                # Increment attempts and set for retry
                await job_repo.increment_attempts(job_id, str(e))
                # Requeue mechanism
                delay = (job.attempts + 1) * 60 # retry after N minutes
                asyncio.create_task(_delayed_requeue(job_id, delay))

            finally:
                if job_id in _active_downloads:
                    del _active_downloads[job_id]

async def _delayed_requeue(job_id: int, delay_sec: float):
    await asyncio.sleep(delay_sec)
    await queue_download(job_id)

async def download_worker(db_factory: Callable):
    """Background worker that continuously processes the download queue."""
    logger.info("Download worker started.")
    while True:
        try:
            job_id = await _queue.get()
            task = asyncio.create_task(process_job(job_id, db_factory))
            _active_tasks[job_id] = task
            task.add_done_callback(lambda t, jid=job_id: _active_tasks.pop(jid, None))
            _queue.task_done()
        except Exception as e:
            logger.error(f"Error in download worker loop: {e}")
            await asyncio.sleep(5)

async def rehydrate_jobs(db_factory: Callable):
    """Called on startup to requeue pending/downloading jobs."""
    async with db_factory() as db:
        job_repo = DownloadJobRepository(db)
        pending_jobs = await job_repo.list_pending_and_retry()
        for job in pending_jobs:
            await queue_download(job.id)
        logger.info(f"Rehydrated {len(pending_jobs)} download jobs.")
