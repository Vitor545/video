"""
CourseImporter — orquestra o pipeline de sincronização Telegram → Banco.

Pipeline:
  1. telegram.collect_raw_messages    → mensagens brutas (headers + vídeos)
  2. channel_parser.extract_channel_structure → JSON canônico via GPT-4o
  3. import_from_ai_json              → upsert idempotente no Postgres

O JSON canônico é também salvo em disco (sync_audit/) para auditoria/debug.
"""
import json
import logging
import time
from pathlib import Path
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.entities import ImportResult, SyncPhase
from app.infrastructure.repositories import CourseRepository, VideoRepository

logger = logging.getLogger(__name__)


# Estado em memória — uma entrada por integração
_sync_status: dict[int, dict] = {}


def get_sync_status(integration_id: int) -> dict | None:
    return _sync_status.get(integration_id)


def _set_status(
    integration_id: int,
    phase: SyncPhase,
    progress: int = 0,
    total: int = 0,
    error: str | None = None,
) -> None:
    _sync_status[integration_id] = {
        "phase": phase.value,
        "progress": progress,
        "total": total,
        "error": error,
    }


def _audit_path(integration_id: int) -> Path:
    base = Path(settings.telegram_session_path).parent / "sync_audit"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"integration_{integration_id}_{int(time.time())}.json"


# --------------------------------------------------------------------------
# Importação no banco (consome o JSON canônico produzido pelo channel_parser)
# --------------------------------------------------------------------------

async def import_from_ai_json(
    course_json: dict,
    db: AsyncSession,
    course_id: int | None = None,
) -> ImportResult:
    course_repo = CourseRepository(db)
    video_repo = VideoRepository(db)

    source_name = course_json.get("sourceName", "")
    course_title = course_json.get("courseTitle", source_name)
    description = course_json.get("description", "")

    # Resolução do curso: id explícito > source_name > criar
    course = None
    if course_id:
        course = await course_repo.get_by_id(course_id)
    if course is None:
        course = await course_repo.get_by_source(source_name)
    if course is None:
        course = await course_repo.create(
            title=course_title,
            telegram_channel=source_name,
            description=description,
            source_name=source_name,
        )
        logger.info("Curso criado: '%s' (id=%d)", course_title, course.id)
    else:
        course.source_name = source_name
        await db.commit()
        logger.info("Curso reutilizado: '%s' (id=%d)", course.title, course.id)

    total_new = 0
    total_updated = 0
    total_duration = 0
    global_order = 0

    for module in course_json.get("modules", []):
        module_title = (module.get("moduleTitle") or "Geral").strip()
        for lesson in module.get("lessons", []):
            file_id = str(lesson.get("fileId", "")).strip()
            if not file_id.isdigit():
                logger.warning("Pulando lesson com fileId inválido: %r", file_id)
                continue

            msg_id = int(file_id)
            duration_seconds = int(lesson.get("durationSeconds") or 0)
            file_size = lesson.get("fileSize")
            title = (lesson.get("lessonTitle") or f"Aula {msg_id}").strip()
            fcode = lesson.get("fcode")
            media_type = (lesson.get("mediaType") or "video").strip().lower()
            mime_type = lesson.get("mimeType")
            original_filename = lesson.get("originalFilename")
            file_ext = lesson.get("fileExt")

            global_order += 1
            _, created = await video_repo.upsert_by_msg_id(
                msg_id=msg_id,
                course_id=course.id,
                module_name=module_title,
                title=title,
                order_index=global_order,
                duration_seconds=duration_seconds,
                file_size=file_size,
                source_name=source_name,
                fcode=fcode,
                media_type=media_type,
                mime_type=mime_type,
                original_filename=original_filename,
                file_ext=file_ext,
            )

            total_duration += duration_seconds
            if created:
                total_new += 1
            else:
                total_updated += 1

    total = total_new + total_updated
    await course_repo.update_stats(
        course_id=course.id,
        total_videos=total,
        total_duration_seconds=total_duration,
    )

    logger.info(
        "Import: curso_id=%d, total=%d, novos=%d, atualizados=%d",
        course.id, total, total_new, total_updated,
    )
    return ImportResult(
        course_id=course.id,
        total=total,
        new=total_new,
        updated=total_updated,
    )


# --------------------------------------------------------------------------
# Pipeline de extração (rodado em background)
# --------------------------------------------------------------------------

async def run_extraction(
    integration_id: int,
    channel_name: str,
    api_id: int,
    api_hash: str,
    session_path: str,
    db_factory: Callable,
    course_id: int | None = None,
) -> ImportResult:
    """Executa coleta → extração IA → import. Atualiza _sync_status a cada fase."""
    from app.infrastructure import telegram as tg_service
    from app.infrastructure.channel_parser import extract_channel_structure

    try:
        # FASE 1 — Coleta de mensagens brutas
        _set_status(integration_id, SyncPhase.COLLECTING, 0, 0)
        logger.info("[integration=%d] Conectando ao Telegram…", integration_id)
        client = await tg_service.connect(api_id, api_hash, session_path)

        def progress_cb(current: int, total):
            _set_status(integration_id, SyncPhase.COLLECTING, current, total or 0)

        raw_messages = await tg_service.collect_raw_messages(
            client, channel_name, progress_callback=progress_cb,
        )
        final_collect = get_sync_status(integration_id) or {}
        scanned = int(final_collect.get("progress") or 0)
        scanned_total = int(final_collect.get("total") or 0) or scanned
        _set_status(integration_id, SyncPhase.COLLECTING, scanned_total, scanned_total)

        header_count = sum(1 for m in raw_messages if m.get("is_header"))
        video_count = len(raw_messages) - header_count
        logger.info(
            "[integration=%d] Coletadas %d mensagens (%d guia, %d vídeos).",
            integration_id, len(raw_messages), header_count, video_count,
        )

        # FASE 2 — Extração via IA
        _set_status(integration_id, SyncPhase.EXTRACTING, 0, 1)
        logger.info("[integration=%d] Extraindo estrutura via gpt-4o…", integration_id)
        def extracting_progress_cb(current: int, total: int):
            _set_status(integration_id, SyncPhase.EXTRACTING, int(current), int(total or 0))

        course_json = await extract_channel_structure(
            raw_messages,
            channel_name,
            progress_callback=extracting_progress_cb,
        )

        # Audit em disco
        audit = _audit_path(integration_id)
        audit.write_text(
            json.dumps(course_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("[integration=%d] Audit JSON salvo em %s", integration_id, audit)

        module_count = len(course_json.get("modules", []))
        lesson_count = sum(
            len(m.get("lessons", [])) for m in course_json.get("modules", [])
        )
        final_extract = get_sync_status(integration_id) or {}
        extracted = int(final_extract.get("progress") or 0)
        extracted_total = int(final_extract.get("total") or 0) or extracted or 1
        _set_status(integration_id, SyncPhase.EXTRACTING, extracted_total, extracted_total)
        logger.info(
            "[integration=%d] Extração: %d módulos, %d aulas.",
            integration_id, module_count, lesson_count,
        )

        # FASE 3 — Import no banco
        _set_status(integration_id, SyncPhase.IMPORTING, 0, lesson_count)
        async with db_factory() as db:
            result = await import_from_ai_json(course_json, db, course_id=course_id)

        _set_status(integration_id, SyncPhase.DONE, result.total, result.total)
        logger.info("[integration=%d] Sync concluído: %s", integration_id, result)
        return result

    except Exception as e:
        logger.error(
            "[integration=%d] Falha na extração: %s", integration_id, e, exc_info=True,
        )
        _set_status(integration_id, SyncPhase.ERROR, 0, 0, error=str(e))
        raise
