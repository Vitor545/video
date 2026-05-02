from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class DownloadStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DONE = "done"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"


class SyncPhase(StrEnum):
    COLLECTING = "collecting"
    EXTRACTING = "extracting"
    IMPORTING = "importing"
    DONE = "done"
    ERROR = "error"


@dataclass
class ImportResult:
    course_id: int
    total: int
    new: int
    updated: int


@dataclass
class UserEntity:
    id: int
    email: str
    name: str
    created_at: datetime


@dataclass
class CourseEntity:
    id: int
    title: str
    telegram_channel: str
    total_videos: int
    total_duration_seconds: int
    thumbnail_url: str | None


@dataclass
class VideoEntity:
    id: int
    course_id: int
    module_name: str
    title: str
    fcode: str
    duration_seconds: int
    order_index: int
    storage_path: str | None
    download_status: DownloadStatus


@dataclass
class WatchHistoryEntry:
    id: int
    user_id: int
    video_id: int
    progress_seconds: int
    completed: bool
    watched_at: datetime
