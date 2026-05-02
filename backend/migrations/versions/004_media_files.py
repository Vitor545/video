"""M4 — Suporte a arquivos (documentos) além de vídeos

Revision ID: 004
Revises: 003
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column("media_type", sa.String(length=20), server_default="video", nullable=False),
    )
    op.add_column(
        "videos",
        sa.Column("mime_type", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("original_filename", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("file_ext", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("videos", "file_ext")
    op.drop_column("videos", "original_filename")
    op.drop_column("videos", "mime_type")
    op.drop_column("videos", "media_type")
