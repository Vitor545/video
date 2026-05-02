from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://devops:devops@db:5432/devops_platform"
    sync_database_url: str = "postgresql+psycopg2://devops:devops@db:5432/devops_platform"
    secret_key: str = "super-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Telegram / IA (M2)
    openai_api_key: str = ""
    telegram_session_path: str = "/app/telegram_data/session"
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_phone: str = ""

    # Armazenamento local
    storage_dir: str = "/app/storage"
    storage_total_gb: float = 200.0

    # Compressão de vídeo (ffmpeg)
    video_compress_enabled: bool = True
    video_compress_codec: str = "libx264"
    video_compress_crf: int = 28
    video_compress_preset: str = "medium"
    video_audio_bitrate: str = "96k"

    class Config:
        env_file = ".env"


settings = Settings()
