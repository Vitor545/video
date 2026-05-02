"""
Management router — integrações Telegram + saúde do sistema.

Endpoints:
  GET    /management/integrations              Lista todas as integrações
  POST   /management/integrations              Cria nova integração
  DELETE /management/integrations/{id}         Remove integração
  POST   /management/integrations/{id}/sync    Inicia extração IA (background)
  POST   /management/integrations/sync-all     Sincroniza todas
  GET    /management/integrations/{id}/sync/status  Progresso da extração
  GET    /management/system/health             Status: telegram, postgres, seaweed, storage
"""
import asyncio
import logging
from datetime import datetime, UTC

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.infrastructure.repositories import TelegramConfigRepository, CourseRepository
from app.application.sync import run_extraction, get_sync_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/management", tags=["management"])


# ---------------------------------------------------------------------------
# Schemas de entrada/saída
# ---------------------------------------------------------------------------

class IntegrationIn(BaseModel):
    name: str
    api_id: str | None = None
    api_hash: str | None = None
    channel_name: str
    phone: str | None = None
    course_id: int | None = None
    auto_sync: bool = True  # Iniciar extração automaticamente após criar


class IntegrationOut(BaseModel):
    id: int
    name: str
    api_id: str
    channel_name: str
    phone: str | None
    is_active: bool
    course_id: int | None
    created_at: datetime
    sync_status: dict | None = None

    class Config:
        from_attributes = True


class SyncStatusOut(BaseModel):
    phase: str   # collecting | extracting | importing | done | error
    progress: int
    total: int
    error: str | None = None


# ---------------------------------------------------------------------------
# Legacy endpoints (compatibilidade com frontend antigo)
# ---------------------------------------------------------------------------

class TelegramConfigIn(BaseModel):
    api_id: str
    api_hash: str
    channel_name: str
    phone: str | None = None


@router.get("/telegram", include_in_schema=False)
async def get_config_legacy(db: AsyncSession = Depends(get_db)):
    return await TelegramConfigRepository(db).get_active()


@router.post("/telegram", include_in_schema=False)
async def save_config_legacy(data: TelegramConfigIn, db: AsyncSession = Depends(get_db)):
    return await TelegramConfigRepository(db).upsert(**data.model_dump())


# ---------------------------------------------------------------------------
# Integrations CRUD
# ---------------------------------------------------------------------------

@router.get("/integrations", response_model=list[IntegrationOut])
async def list_integrations(db: AsyncSession = Depends(get_db)):
    """Lista todas as integrações Telegram com status de sync em memória."""
    configs = await TelegramConfigRepository(db).list_all()
    result = []
    for cfg in configs:
        out = IntegrationOut(
            id=cfg.id,
            name=cfg.name or cfg.channel_name,
            api_id=cfg.api_id,
            channel_name=cfg.channel_name,
            phone=cfg.phone,
            is_active=cfg.is_active,
            course_id=cfg.course_id,
            created_at=cfg.created_at,
            sync_status=get_sync_status(cfg.id),
        )
        result.append(out)
    return result


@router.post("/integrations", response_model=IntegrationOut, status_code=201)
async def create_integration(
    data: IntegrationIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Cria nova integração Telegram e opcionalmente inicia a extração por IA."""
    api_id = (data.api_id or settings.telegram_api_id or "").strip()
    api_hash = (data.api_hash or settings.telegram_api_hash or "").strip()
    if not api_id or not api_hash:
        raise HTTPException(
            status_code=400,
            detail="API ID e API Hash não configurados. Informe na integração ou defina TELEGRAM_API_ID/TELEGRAM_API_HASH no ambiente.",
        )

    phone = (data.phone or settings.telegram_phone or "").strip() or None

    repo = TelegramConfigRepository(db)
    config = await repo.create(
        name=data.name,
        api_id=api_id,
        api_hash=api_hash,
        channel_name=data.channel_name,
        phone=phone,
        course_id=data.course_id,
    )

    if data.auto_sync:
        _schedule_sync(config.id, config.channel_name, config.api_id, config.api_hash)

    return IntegrationOut(
        id=config.id,
        name=config.name,
        api_id=config.api_id,
        channel_name=config.channel_name,
        phone=config.phone,
        is_active=config.is_active,
        course_id=config.course_id,
        created_at=config.created_at,
        sync_status=get_sync_status(config.id),
    )


@router.delete("/integrations/{integration_id}", status_code=204)
async def delete_integration(integration_id: int, db: AsyncSession = Depends(get_db)):
    """Remove uma integração pelo ID."""
    deleted = await TelegramConfigRepository(db).delete(integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integração não encontrada")


@router.post("/integrations/{integration_id}/sync", status_code=202)
async def sync_integration(integration_id: int, db: AsyncSession = Depends(get_db)):
    """Inicia ou reinicia a extração por IA para uma integração específica (background)."""
    config = await TelegramConfigRepository(db).get_by_id(integration_id)
    if not config:
        raise HTTPException(status_code=404, detail="Integração não encontrada")

    status = get_sync_status(integration_id)
    if status and status["phase"] in ("collecting", "extracting", "importing"):
        raise HTTPException(status_code=409, detail="Extração já em andamento para esta integração")

    _schedule_sync(integration_id, config.channel_name, config.api_id, config.api_hash, course_id=config.course_id)
    return {"message": "Extração iniciada", "integration_id": integration_id}


@router.post("/integrations/sync-all", status_code=202)
async def sync_all_integrations(db: AsyncSession = Depends(get_db)):
    """Inicia a extração para todas as integrações ativas (background)."""
    configs = await TelegramConfigRepository(db).list_all()
    started = []
    for config in configs:
        if not config.is_active:
            continue
        status = get_sync_status(config.id)
        if status and status["phase"] in ("collecting", "extracting", "importing"):
            continue  # já rodando
        _schedule_sync(config.id, config.channel_name, config.api_id, config.api_hash, course_id=config.course_id)
        started.append(config.id)
    return {"message": f"{len(started)} extração(ões) iniciada(s)", "integration_ids": started}


@router.get("/integrations/{integration_id}/sync/status", response_model=SyncStatusOut)
async def get_integration_sync_status(integration_id: int):
    """Retorna o progresso da extração IA em andamento para uma integração."""
    status = get_sync_status(integration_id)
    if not status:
        return SyncStatusOut(phase="idle", progress=0, total=0)
    return SyncStatusOut(**status)


# ---------------------------------------------------------------------------
# Telegram Auth (session setup via API)
# ---------------------------------------------------------------------------

# Armazena phone_code_hash temporariamente em memória (auth global)
_pending_auth: dict[int, dict] = {}


class SendCodeIn(BaseModel):
    integration_id: int | None = None


class VerifyCodeIn(BaseModel):
    integration_id: int | None = None
    code: str


@router.post("/telegram/send-code")
async def telegram_send_code(data: SendCodeIn | None = Body(None), db: AsyncSession = Depends(get_db)):
    api_id = (settings.telegram_api_id or "").strip()
    api_hash = (settings.telegram_api_hash or "").strip()
    phone = (settings.telegram_phone or "").strip()
    if not api_id or not api_hash:
        raise HTTPException(400, "Credenciais do Telegram não configuradas. Defina TELEGRAM_API_ID/TELEGRAM_API_HASH no ambiente.")
    if not phone:
        raise HTTPException(400, "Número de telefone não configurado. Defina TELEGRAM_PHONE no ambiente.")

    try:
        from telethon import TelegramClient
        session_path = settings.telegram_session_path
        client = TelegramClient(session_path, int(api_id), api_hash)
        await client.connect()
        result = await client.send_code_request(phone)
        await client.disconnect()
        _pending_auth[0] = {"phone": phone, "phone_code_hash": result.phone_code_hash}
        return {"detail": f"Código enviado para {phone}"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/telegram/verify-code")
async def telegram_verify_code(data: VerifyCodeIn, db: AsyncSession = Depends(get_db)):
    state = _pending_auth.get(0)
    if not state:
        raise HTTPException(400, "Nenhum código pendente. Chame /send-code primeiro.")
    api_id = (settings.telegram_api_id or "").strip()
    api_hash = (settings.telegram_api_hash or "").strip()
    if not api_id or not api_hash:
        raise HTTPException(400, "Credenciais do Telegram não configuradas. Defina TELEGRAM_API_ID/TELEGRAM_API_HASH no ambiente.")

    try:
        from telethon import TelegramClient
        session_path = settings.telegram_session_path
        client = TelegramClient(session_path, int(api_id), api_hash)
        await client.connect()
        await client.sign_in(state["phone"], data.code, phone_code_hash=state["phone_code_hash"])
        me = await client.get_me()
        await client.disconnect()
        _pending_auth.pop(0, None)
        return {"detail": f"Autenticado como {me.first_name} (@{me.username})"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

@router.get("/system/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    """
    Verifica saúde dos componentes: postgres, seaweed, storage.
    """
    # Postgres
    postgres_ok = False
    try:
        await db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        pass

    # SeaweedFS — verifica via S3 endpoint (master não exposto externamente)
    seaweed_ok = False
    if (settings.storage_backend or "s3").lower() != "local":
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(settings.s3_endpoint, follow_redirects=True)
                seaweed_ok = resp.status_code < 500
        except Exception:
            pass
    else:
        seaweed_ok = True

    # Storage usado
    storage_used_gb = 0.0
    try:
        result = await db.execute(
            text("SELECT COALESCE(SUM(file_size), 0) FROM videos WHERE download_status = 'done'")
        )
        total_bytes = result.scalar() or 0
        storage_used_gb = round(total_bytes / (1024 ** 3), 2)
    except Exception:
        pass

    return {
        "postgres": postgres_ok,
        "seaweed": seaweed_ok,
        "storage_used_gb": storage_used_gb,
        "storage_total_gb": settings.storage_total_gb,
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _schedule_sync(integration_id: int, channel_name: str, api_id: str, api_hash: str, course_id: int | None = None) -> None:
    """Agenda run_extraction como asyncio.create_task (fire-and-forget)."""
    session_path = settings.telegram_session_path
    asyncio.create_task(
        run_extraction(
            integration_id=integration_id,
            channel_name=channel_name,
            api_id=int(api_id),
            api_hash=api_hash,
            session_path=session_path,
            db_factory=AsyncSessionLocal,
            course_id=course_id,
        )
    )
