"""M2 — Campos de extração IA em Video e Course + reestruturação TelegramConfig

Revision ID: 002
Revises: 001
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Video: novos campos de extração por IA
    # -----------------------------------------------------------------------
    op.add_column("videos", sa.Column("msg_id", sa.BigInteger, nullable=True))
    op.add_column("videos", sa.Column("file_size", sa.BigInteger, nullable=True))
    op.add_column("videos", sa.Column("source_name", sa.String(255), nullable=True))
    op.create_index("ix_videos_msg_id", "videos", ["msg_id"])

    # -----------------------------------------------------------------------
    # Course: source_name para re-scan idempotente
    # -----------------------------------------------------------------------
    op.add_column("courses", sa.Column("source_name", sa.String(255), nullable=True))
    op.create_index("ix_courses_source_name", "courses", ["source_name"])

    # -----------------------------------------------------------------------
    # TelegramConfig: nome amigável + vínculo com Course (suporte a múltiplos)
    # -----------------------------------------------------------------------
    op.add_column(
        "telegram_configs",
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "telegram_configs",
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id"), nullable=True),
    )
    op.create_index("ix_telegram_configs_course_id", "telegram_configs", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_telegram_configs_course_id", "telegram_configs")
    op.drop_column("telegram_configs", "course_id")
    op.drop_column("telegram_configs", "name")

    op.drop_index("ix_courses_source_name", "courses")
    op.drop_column("courses", "source_name")

    op.drop_index("ix_videos_msg_id", "videos")
    op.drop_column("videos", "source_name")
    op.drop_column("videos", "file_size")
    op.drop_column("videos", "msg_id")
