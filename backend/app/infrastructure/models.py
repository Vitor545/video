from datetime import datetime, UTC
from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime, Boolean, Enum as SAEnum, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database import Base
from app.domain.entities import DownloadStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    history: Mapped[list["WatchHistory"]] = relationship(back_populates="user")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_channel: Mapped[str] = mapped_column(String(255))
    total_videos: Mapped[int] = mapped_column(default=0)
    total_duration_seconds: Mapped[int] = mapped_column(default=0)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # M2: identificador para re-scan idempotente
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    videos: Mapped[list["Video"]] = relationship(back_populates="course", order_by="Video.order_index")
    telegram_configs: Mapped[list["TelegramConfig"]] = relationship(back_populates="course")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    module_name: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    fcode: Mapped[str] = mapped_column(String(20), index=True)
    media_type: Mapped[str] = mapped_column(String(20), default="video")
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_ext: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(default=0)
    order_index: Mapped[int] = mapped_column(default=0)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    download_status: Mapped[DownloadStatus] = mapped_column(
        SAEnum(DownloadStatus, name="downloadstatus", create_type=False, values_callable=lambda x: [e.value for e in x]), default=DownloadStatus.PENDING
    )
    # M2: campos de extração por IA
    msg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    course: Mapped["Course"] = relationship(back_populates="videos")
    history: Mapped[list["WatchHistory"]] = relationship(back_populates="video")


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    progress_seconds: Mapped[int] = mapped_column(default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    user: Mapped["User"] = relationship(back_populates="history")
    video: Mapped["Video"] = relationship(back_populates="history")


class TelegramConfig(Base):
    __tablename__ = "telegram_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # M2: nome amigável e vínculo com Course
    name: Mapped[str] = mapped_column(String(255), default="")
    api_id: Mapped[str] = mapped_column(String(50))
    api_hash: Mapped[str] = mapped_column(String(255))
    channel_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    course: Mapped["Course | None"] = relationship(back_populates="telegram_configs")


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    video: Mapped["Video"] = relationship()
    status: Mapped[DownloadStatus] = mapped_column(
        SAEnum(DownloadStatus, name="downloadstatus", create_constraint=False, values_callable=lambda x: [e.value for e in x]), default=DownloadStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
