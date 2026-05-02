"""M3 — Resiliência de downloads em DownloadJob

Revision ID: 003
Revises: 002
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar novas colunas em download_jobs
    op.add_column("download_jobs", sa.Column("attempts", sa.Integer, server_default="0", nullable=False))
    op.add_column("download_jobs", sa.Column("next_retry_at", sa.DateTime, nullable=True))

    # O enum downloadstatus precisa ser atualizado com 'retry_pending'.
    # PostgreSQL não suporta ALTER TYPE ... ADD VALUE em bloco transacional simples.
    # Usaremos COMMIT e ADD VALUE.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE downloadstatus ADD VALUE IF NOT EXISTS 'retry_pending'")


def downgrade() -> None:
    op.drop_column("download_jobs", "next_retry_at")
    op.drop_column("download_jobs", "attempts")
    # Não há suporte fácil para remover valores de Enum no PostgreSQL sem recriar o tipo inteiro.
    # Mantemos o enum como está.
