"""
TelegramService — coleta mensagens brutas de um canal Telegram via Telethon.

Não faz parsing semântico: apenas retorna dados brutos (msg_id, caption,
duration_seconds, file_size_bytes) para o AIExtractor processar.
"""
import asyncio
import logging
import time
from pathlib import Path
import mimetypes
from typing import TypedDict

logger = logging.getLogger(__name__)


class RawMessage(TypedDict):
    msg_id: int
    caption: str
    duration_seconds: int
    file_size_bytes: int | None
    media_type: str
    mime_type: str | None
    original_filename: str | None


async def connect(api_id: int, api_hash: str, session_path: str):
    """
    Retorna um TelegramClient conectado, reutilizando do cache compartilhado.
    Garante apenas 1 conexão SQLite por session_path para evitar 'database is locked'.
    """
    from app.infrastructure.telegram_clients import get_client
    return await get_client(api_id, api_hash, session_path)


async def collect_raw_messages(
    client,
    channel_name: str,
    progress_callback=None,
) -> list[RawMessage]:
    """
    Itera TODAS as mensagens do canal coletando apenas as que têm vídeo/documento.

    Args:
        client: TelegramClient conectado.
        channel_name: Nome/username do canal (ex: "@devopspro2" ou "DevOps Pro 2").
        progress_callback: Callable(current, total) opcional para reportar progresso.

    Returns:
        Lista de RawMessage com dados brutos de cada vídeo encontrado.
    """
    messages: list[RawMessage] = []

    try:
        entity = await client.get_entity(channel_name)
    except Exception:
        # Cache de diálogos pode estar vazio — busca todos os diálogos primeiro
        logger.info("get_entity falhou, carregando diálogos para popular cache...")
        await client.get_dialogs()
        try:
            entity = await client.get_entity(channel_name)
        except Exception as e:
            logger.error("Falha ao buscar entidade do canal '%s' mesmo após get_dialogs: %s", channel_name, e)
            raise

    logger.info("Iniciando coleta de mensagens do canal: %s", channel_name)

    total_count = 0
    try:
        probe = await client.get_messages(entity, limit=1)
        total_count = int(getattr(probe, "total", 0) or 0)
    except Exception:
        total_count = 0

    total_seen = 0
    last_report_t = time.monotonic()
    last_report_seen = 0
    async for msg in client.iter_messages(entity, reverse=True):
        total_seen += 1
        if progress_callback:
            now = time.monotonic()
            if (total_seen - last_report_seen) >= 250 or (now - last_report_t) >= 3.0:
                last_report_t = now
                last_report_seen = total_seen
                progress_callback(total_seen, total_count or None)

        text = (msg.message or "").strip()

        # Mensagem de texto pura ou com preview de link (WebPage) — pode ser cabeçalho de módulo
        # Sem limite de tamanho: headers de módulo com muitos vídeos podem ser grandes
        is_webpage = msg.media is not None and type(msg.media).__name__ == "MessageMediaWebPage"
        if (not msg.media or is_webpage) and text:
            messages.append({
                "msg_id": msg.id,
                "caption": text,
                "duration_seconds": 0,
                "file_size_bytes": None,
                "media_type": "header",
                "mime_type": None,
                "original_filename": None,
                "is_header": True,
            })
            continue

        if not msg.media:
            continue

        has_document = hasattr(msg.media, "document") and msg.media.document is not None
        has_video = hasattr(msg.media, "video") and msg.media.video is not None

        if not (has_video or has_document):
            continue

        # Extrai duração e tamanho
        duration_seconds = 0
        file_size_bytes = None
        mime_type = None
        original_filename = None
        media_type = "video"

        if has_document:
            doc = msg.media.document
            mime = (getattr(doc, "mime_type", "") or "").lower()
            mime_type = mime or None
            attrs = list(getattr(doc, "attributes", []) or [])
            for attr in attrs:
                if hasattr(attr, "file_name") and getattr(attr, "file_name", None):
                    original_filename = str(getattr(attr, "file_name"))

            if not original_filename:
                try:
                    if hasattr(msg, "file") and msg.file and getattr(msg.file, "name", None):
                        original_filename = str(getattr(msg.file, "name"))
                except Exception:
                    original_filename = None

            is_video_attr = any(type(a).__name__ == "DocumentAttributeVideo" for a in attrs)
            is_audio_attr = any(type(a).__name__ == "DocumentAttributeAudio" for a in attrs)
            is_video_mime = mime.startswith("video/")

            media_type = "video" if (is_video_mime or is_video_attr) else "file"

            duration_seconds = 0
            if is_video_attr or is_audio_attr:
                for attr in attrs:
                    if hasattr(attr, "duration") and getattr(attr, "duration", None):
                        duration_seconds = int(attr.duration)
                        break

            if not mime_type and original_filename:
                guessed_mime, _ = mimetypes.guess_type(original_filename)
                mime_type = guessed_mime or None

            file_size_bytes = getattr(doc, "size", None)
        elif has_video:
            vid = msg.media.video
            duration_seconds = getattr(vid, "duration", 0) or 0
            file_size_bytes = getattr(vid, "size", None)

        caption = msg.message or ""

        messages.append({
            "msg_id": msg.id,
            "caption": caption.strip(),
            "duration_seconds": duration_seconds,
            "file_size_bytes": file_size_bytes,
            "media_type": media_type,
            "mime_type": mime_type,
            "original_filename": original_filename,
            "is_header": False,
        })

    if progress_callback:
        progress_callback(total_seen, total_count or None)

    logger.info(
        "Coleta finalizada: %d mensagens totais, %d vídeos encontrados",
        total_seen,
        len(messages),
    )
    return messages


async def download_video(
    client, 
    msg_id: int, 
    dest_dir: Path, 
    channel_name: str,
    progress_callback=None
) -> Path:
    """
    Baixa a mídia de uma mensagem Telegram para o diretório dest_dir.

    Args:
        client: TelegramClient conectado.
        msg_id: ID da mensagem com o vídeo.
        dest_dir: Diretório de destino para o arquivo baixado.
        channel_name: Canal onde a mensagem está (para `get_messages`).
        progress_callback: Callable(current_bytes, total_bytes)

    Returns:
        Path do arquivo baixado.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        entity = await client.get_entity(channel_name)
        msg = await client.get_messages(entity, ids=msg_id)
    except Exception as e:
        raise Exception(f"Erro ao buscar mensagem {msg_id}: {e}") from e

    if msg is None:
        raise FileNotFoundError(f"Mensagem {msg_id} não encontrada (pode ter sido deletada)")

    ext = ".mp4"
    try:
        if msg.media is not None and hasattr(msg.media, "document") and msg.media.document is not None:
            doc = msg.media.document
            mime = (getattr(doc, "mime_type", "") or "").lower()
            filename = None
            for attr in getattr(doc, "attributes", []):
                if hasattr(attr, "file_name") and getattr(attr, "file_name", None):
                    filename = str(getattr(attr, "file_name"))
                    break
            if filename:
                suffix = Path(filename).suffix
                if suffix:
                    ext = suffix
                else:
                    guessed = mimetypes.guess_extension(mime or "") if mime else None
                    ext = guessed or ".bin"
            else:
                guessed = mimetypes.guess_extension(mime or "") if mime else None
                ext = guessed or (".mp4" if mime.startswith("video/") else ".bin")
    except Exception:
        ext = ".mp4"

    dest_path = dest_dir / f"{msg_id}{ext}"

    total_size = 0
    try:
        if msg.media is not None and hasattr(msg.media, "document") and msg.media.document is not None:
            total_size = int(getattr(msg.media.document, "size", 0) or 0)
    except Exception:
        total_size = 0

    # Chunks de 512KB (8x o padrão de 64KB do Telethon). request_size precisa
    # ser múltiplo de 4096 e divisor de 1MB; 524288 é o teto seguro.
    CHUNK = 512 * 1024
    downloaded = 0
    try:
        with open(dest_path, "wb") as f:
            async for chunk in client.iter_download(msg, request_size=CHUNK):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total_size)
    except Exception as e:
        try:
            if dest_path.exists():
                dest_path.unlink()
        except OSError:
            pass
        error_str = str(e).lower()
        if "flood" in error_str or "floodwait" in error_str:
            raise RuntimeError(f"TelegramFloodError: {e}") from e
        raise

    if not dest_path.exists():
        raise FileNotFoundError(f"Download falhou: arquivo {dest_path} não foi criado")

    return dest_path
