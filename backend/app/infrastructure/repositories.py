from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.infrastructure.models import User, Course, Video, WatchHistory, TelegramConfig, DownloadJob
from app.domain.entities import DownloadStatus


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, name: str, hashed_password: str) -> User:
        user = User(email=email, name=name, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user


class CourseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Course]:
        result = await self.db.execute(select(Course).order_by(Course.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, course_id: int) -> Course | None:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        return result.scalar_one_or_none()

    async def get_by_source(self, source_name: str) -> Course | None:
        result = await self.db.execute(
            select(Course).where(Course.source_name == source_name)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        title: str,
        telegram_channel: str,
        description: str | None = None,
        source_name: str | None = None,
    ) -> Course:
        course = Course(
            title=title,
            telegram_channel=telegram_channel,
            description=description,
            source_name=source_name,
        )
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def update_stats(self, course_id: int, total_videos: int, total_duration_seconds: int) -> None:
        course = await self.get_by_id(course_id)
        if course:
            course.total_videos = total_videos
            course.total_duration_seconds = total_duration_seconds
            await self.db.commit()


class VideoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_course(self, course_id: int) -> list[Video]:
        result = await self.db.execute(
            select(Video).where(Video.course_id == course_id).order_by(Video.order_index)
        )
        return list(result.scalars().all())

    async def get_by_id(self, video_id: int) -> Video | None:
        result = await self.db.execute(select(Video).where(Video.id == video_id))
        return result.scalar_one_or_none()

    async def get_by_msg_id(self, msg_id: int, course_id: int) -> Video | None:
        result = await self.db.execute(
            select(Video).where(Video.msg_id == msg_id, Video.course_id == course_id)
        )
        return result.scalar_one_or_none()

    async def upsert_by_msg_id(
        self,
        msg_id: int,
        course_id: int,
        module_name: str,
        title: str,
        order_index: int,
        duration_seconds: int,
        file_size: int | None,
        source_name: str | None = None,
        fcode: str | None = None,
        media_type: str = "video",
        mime_type: str | None = None,
        original_filename: str | None = None,
        file_ext: str | None = None,
    ) -> tuple[Video, bool]:
        """Returns (video, created) where created=True means new record."""
        # Fallback: deriva do msg_id quando o caller não tem o fcode real
        effective_fcode = fcode or f"M{msg_id}"

        existing = await self.get_by_msg_id(msg_id, course_id)
        if existing:
            existing.module_name = module_name
            existing.title = title
            existing.order_index = order_index
            existing.duration_seconds = duration_seconds
            existing.file_size = file_size
            existing.source_name = source_name
            existing.media_type = media_type or existing.media_type or "video"
            existing.mime_type = mime_type
            existing.original_filename = original_filename
            existing.file_ext = file_ext
            # Sobrescreve fcode quando o caller fornece um (extraído do caption real)
            if fcode:
                existing.fcode = fcode
            await self.db.commit()
            await self.db.refresh(existing)
            return existing, False
        else:
            video = Video(
                msg_id=msg_id,
                course_id=course_id,
                module_name=module_name,
                title=title,
                fcode=effective_fcode,
                media_type=media_type or "video",
                mime_type=mime_type,
                original_filename=original_filename,
                file_ext=file_ext,
                order_index=order_index,
                duration_seconds=duration_seconds,
                file_size=file_size,
                source_name=source_name,
            )
            self.db.add(video)
            await self.db.commit()
            await self.db.refresh(video)
            return video, True

    async def update_status(self, video_id: int, status: DownloadStatus, storage_path: str | None = None):
        video = await self.get_by_id(video_id)
        if video:
            video.download_status = status
            if storage_path:
                video.storage_path = storage_path
            await self.db.commit()

    async def update_storage_path(self, video_id: int, storage_path: str | None, file_size: int | None = None) -> None:
        video = await self.get_by_id(video_id)
        if video:
            video.storage_path = storage_path
            if file_size is not None:
                video.file_size = file_size
            await self.db.commit()

    async def update_duration_seconds(self, video_id: int, duration_seconds: int) -> None:
        video = await self.get_by_id(video_id)
        if video:
            video.duration_seconds = max(0, int(duration_seconds))
            await self.db.commit()

    async def list_by_status(self, status: DownloadStatus) -> list[Video]:
        result = await self.db.execute(select(Video).where(Video.download_status == status))
        return list(result.scalars().all())


class WatchHistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recent(self, user_id: int, limit: int = 10) -> list[WatchHistory]:
        result = await self.db.execute(
            select(WatchHistory)
            .where(WatchHistory.user_id == user_id)
            .order_by(desc(WatchHistory.watched_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_for_video(self, user_id: int, video_id: int) -> WatchHistory | None:
        result = await self.db.execute(
            select(WatchHistory).where(
                WatchHistory.user_id == user_id,
                WatchHistory.video_id == video_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_videos(
        self,
        user_id: int,
        video_ids: list[int],
    ) -> dict[int, WatchHistory]:
        """Bulk lookup — devolve dict {video_id: WatchHistory} para vídeos com histórico."""
        if not video_ids:
            return {}
        result = await self.db.execute(
            select(WatchHistory).where(
                WatchHistory.user_id == user_id,
                WatchHistory.video_id.in_(video_ids),
            )
        )
        return {h.video_id: h for h in result.scalars().all()}

    async def upsert(self, user_id: int, video_id: int, progress_seconds: int, completed: bool = False):
        result = await self.db.execute(
            select(WatchHistory).where(
                WatchHistory.user_id == user_id, WatchHistory.video_id == video_id
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.progress_seconds = progress_seconds
            entry.completed = completed
            entry.watched_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            entry = WatchHistory(user_id=user_id, video_id=video_id,
                                 progress_seconds=progress_seconds, completed=completed)
            self.db.add(entry)
        await self.db.commit()


class TelegramConfigRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> TelegramConfig | None:
        result = await self.db.execute(
            select(TelegramConfig).where(TelegramConfig.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[TelegramConfig]:
        result = await self.db.execute(
            select(TelegramConfig).order_by(TelegramConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, config_id: int) -> TelegramConfig | None:
        result = await self.db.execute(
            select(TelegramConfig).where(TelegramConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def list_by_course(self, course_id: int) -> list[TelegramConfig]:
        result = await self.db.execute(
            select(TelegramConfig).where(TelegramConfig.course_id == course_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        name: str,
        api_id: str,
        api_hash: str,
        channel_name: str,
        phone: str | None = None,
        course_id: int | None = None,
    ) -> TelegramConfig:
        config = TelegramConfig(
            name=name,
            api_id=api_id,
            api_hash=api_hash,
            channel_name=channel_name,
            phone=phone,
            course_id=course_id,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete(self, config_id: int) -> bool:
        config = await self.get_by_id(config_id)
        if config:
            await self.db.delete(config)
            await self.db.commit()
            return True
        return False

    async def upsert(self, api_id: str, api_hash: str, channel_name: str, phone: str | None = None) -> TelegramConfig:
        """Legacy single-config upsert — kept for backward compat."""
        config = await self.get_active()
        if config:
            config.api_id = api_id
            config.api_hash = api_hash
            config.channel_name = channel_name
            if phone:
                config.phone = phone
        else:
            config = TelegramConfig(api_id=api_id, api_hash=api_hash,
                                    channel_name=channel_name, phone=phone)
            self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config


class DownloadJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, job_id: int) -> DownloadJob | None:
        result = await self.db.execute(select(DownloadJob).where(DownloadJob.id == job_id))
        return result.scalar_one_or_none()

    async def get_by_video(self, video_id: int) -> DownloadJob | None:
        result = await self.db.execute(
            select(DownloadJob).where(DownloadJob.video_id == video_id).order_by(DownloadJob.created_at.desc())
        )
        return result.scalars().first()

    async def create(self, video_id: int) -> DownloadJob:
        job = DownloadJob(video_id=video_id, status=DownloadStatus.PENDING)
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def set_downloading(self, job_id: int):
        from datetime import datetime, UTC
        job = await self.get(job_id)
        if job:
            job.status = DownloadStatus.DOWNLOADING
            if not job.started_at:
                job.started_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()

    async def set_done(self, job_id: int):
        from datetime import datetime, UTC
        job = await self.get(job_id)
        if job:
            job.status = DownloadStatus.DONE
            job.finished_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()

    async def set_failed(self, job_id: int, error_message: str):
        from datetime import datetime, UTC
        job = await self.get(job_id)
        if job:
            job.status = DownloadStatus.FAILED
            job.error_message = error_message
            job.finished_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()

    async def increment_attempts(self, job_id: int, error_message: str) -> DownloadJob | None:
        from datetime import datetime, UTC, timedelta
        job = await self.get(job_id)
        if job:
            job.attempts += 1
            job.error_message = error_message
            job.status = DownloadStatus.RETRY_PENDING
            # next retry logic handled elsewhere, just add current time + dummy offset here if needed
            # we'll do the sleep in the worker, so we can just save it
            job.next_retry_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=job.attempts)
            await self.db.commit()
            await self.db.refresh(job)
        return job

    async def list_pending_and_retry(self) -> list[DownloadJob]:
        result = await self.db.execute(
            select(DownloadJob).where(
                DownloadJob.status.in_([
                    DownloadStatus.PENDING, 
                    DownloadStatus.RETRY_PENDING, 
                    DownloadStatus.DOWNLOADING
                ])
            ).order_by(DownloadJob.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_all_with_videos(self) -> list[DownloadJob]:
        # Carrega job, vídeo associado e curso associado
        from sqlalchemy.orm import selectinload
        from app.infrastructure.models import Video
        result = await self.db.execute(
            select(DownloadJob)
            .options(
                selectinload(DownloadJob.video).selectinload(Video.course)
            )
            .order_by(DownloadJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def cancel(self, job_id: int) -> bool:
        job = await self.get(job_id)
        if job and job.status in (DownloadStatus.PENDING, DownloadStatus.RETRY_PENDING):
            await self.db.delete(job)
            await self.db.commit()
            return True
        return False
