"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("telegram_channel", sa.String(255), nullable=False),
        sa.Column("total_videos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_duration_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("fcode", sa.String(20), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("download_status", sa.Enum("pending", "downloading", "done", "failed",
                                             name="downloadstatus"),
                  nullable=False, server_default="pending"),
    )
    op.create_index("ix_videos_course_id", "videos", ["course_id"])
    op.create_index("ix_videos_fcode", "videos", ["fcode"])

    op.create_table(
        "watch_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("progress_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("watched_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_watch_history_user_id", "watch_history", ["user_id"])

    op.create_table(
        "telegram_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("api_id", sa.String(50), nullable=False),
        sa.Column("api_hash", sa.String(255), nullable=False),
        sa.Column("channel_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "download_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Enum("pending", "downloading", "done", "failed",
                                    name="downloadstatus", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_download_jobs_video_id", "download_jobs", ["video_id"])


def downgrade() -> None:
    op.drop_table("download_jobs")
    op.drop_table("telegram_configs")
    op.drop_table("watch_history")
    op.drop_table("videos")
    op.drop_table("courses")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS downloadstatus")
