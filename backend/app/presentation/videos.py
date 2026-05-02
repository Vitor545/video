"""
Videos router — streaming local com Range + tracking de progresso.

Endpoints:
  GET  /videos/{id}/stream-url    → URL com token HMAC para o player
  GET  /videos/{id}/stream-local  → stream do arquivo local (Range)
  GET  /videos/{id}/download-url  → URL com token HMAC para download
  GET  /videos/{id}/download-local→ download local
  GET  /videos/{id}/stream        → redirect autenticado para o stream
  GET  /videos/{id}/progress      → progresso atual do usuário neste vídeo
  POST /videos/{id}/progress      → salva progresso (auto-save do player)
"""
import base64
import hashlib
import hmac
import time
from pathlib import Path
import mimetypes

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import progress as progress_svc
from app.config import settings
from app.database import get_db
from app.domain.entities import DownloadStatus
from app.infrastructure.repositories import VideoRepository
from app.presentation.auth import get_current_user_id

router = APIRouter(prefix="/videos", tags=["videos"])

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)

def _make_stream_token(video_id: int, expires_in: int) -> str:
    exp = int(time.time()) + int(expires_in)
    payload = f"{video_id}:{exp}".encode()
    sig = hmac.new(settings.secret_key.encode(), payload, hashlib.sha256).digest()
    return _b64url_encode(payload + b"." + sig)

def _verify_stream_token(token: str, expected_video_id: int) -> bool:
    try:
        raw = _b64url_decode(token)
        payload, sig = raw.split(b".", 1)
        expected_sig = hmac.new(settings.secret_key.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        video_id_str, exp_str = payload.decode().split(":", 1)
        if int(video_id_str) != int(expected_video_id):
            return False
        if int(exp_str) < int(time.time()):
            return False
        return True
    except Exception:
        return False

async def _file_iterator(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024 * 2):
    async with aiofiles.open(path, "rb") as f:
        await f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = await f.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk

def _range_stream_response(
    path: Path,
    request: Request,
    media_type: str,
    content_disposition: str | None = None,
) -> StreamingResponse:
    size = path.stat().st_size
    range_header = request.headers.get("range")

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
    }
    if content_disposition:
        headers["Content-Disposition"] = content_disposition
    if not range_header:
        headers["Content-Length"] = str(size)
        return StreamingResponse(_file_iterator(path, 0, size - 1), media_type=media_type, headers=headers)

    if not range_header.startswith("bytes="):
        raise HTTPException(416, "Range inválido")

    start_s, end_s = range_header.replace("bytes=", "", 1).split("-", 1)
    if start_s == "":
        suffix = int(end_s)
        start = max(0, size - suffix)
        end = size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else size - 1

    if start < 0 or end < start or start >= size:
        raise HTTPException(416, "Range fora do arquivo")

    end = min(end, size - 1)
    content_length = end - start + 1
    headers.update(
        {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(content_length),
        }
    )
    return StreamingResponse(
        _file_iterator(path, start, end),
        status_code=206,
        media_type=media_type,
        headers=headers,
    )


class ProgressIn(BaseModel):
    progress_seconds: int = Field(ge=0)
    completed: bool = False


class ProgressOut(BaseModel):
    video_id: int
    progress_seconds: int
    completed: bool


class StreamUrlOut(BaseModel):
    url: str
    expires_in: int


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int


@router.get("/{video_id}/stream-url", response_model=StreamUrlOut)
async def get_stream_url(
    video_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Devolve uma URL com token HMAC (TTL 1h) que o `<video src>` do frontend
    consome — a tag não aceita header Authorization, então o token vai na URL.
    """
    video = await VideoRepository(db).get_by_id(video_id)
    if video is None:
        raise HTTPException(404, "Vídeo não encontrado")

    if video.download_status != DownloadStatus.DONE or not video.storage_path:
        raise HTTPException(409, "Vídeo ainda não foi baixado")

    if (getattr(video, "media_type", "video") or "video").lower() != "video":
        raise HTTPException(409, "Este item não é um vídeo")

    expires = 3600
    token = _make_stream_token(video_id, expires)
    return StreamUrlOut(
        url=f"/api/videos/{video_id}/stream-local?token={token}",
        expires_in=expires,
    )


@router.get("/{video_id}/stream-local")
async def stream_video_local(
    video_id: int,
    request: Request,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not token or not _verify_stream_token(token, video_id):
        raise HTTPException(401, "Token inválido ou expirado")

    video = await VideoRepository(db).get_by_id(video_id)
    if video is None:
        raise HTTPException(404, "Vídeo não encontrado")

    if video.download_status != DownloadStatus.DONE or not video.storage_path:
        raise HTTPException(409, "Vídeo ainda não foi baixado")

    if (getattr(video, "media_type", "video") or "video").lower() != "video":
        raise HTTPException(409, "Este item não é um vídeo")

    storage_root = Path(settings.storage_dir).resolve()
    file_path = (storage_root / video.storage_path).resolve()
    if storage_root not in file_path.parents and file_path != storage_root:
        raise HTTPException(400, "Caminho inválido")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "Arquivo não encontrado")

    return _range_stream_response(file_path, request, media_type="video/mp4")


@router.get("/{video_id}/download-url", response_model=DownloadUrlOut)
async def get_download_url(
    video_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    video = await VideoRepository(db).get_by_id(video_id)
    if video is None:
        raise HTTPException(404, "Item não encontrado")

    if video.download_status != DownloadStatus.DONE or not video.storage_path:
        raise HTTPException(409, "Item ainda não foi baixado")

    expires = 3600
    token = _make_stream_token(video_id, expires)
    return DownloadUrlOut(
        url=f"/api/videos/{video_id}/download-local?token={token}",
        expires_in=expires,
    )


@router.get("/{video_id}/download-local")
async def download_local(
    video_id: int,
    request: Request,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not token or not _verify_stream_token(token, video_id):
        raise HTTPException(401, "Token inválido ou expirado")

    video = await VideoRepository(db).get_by_id(video_id)
    if video is None:
        raise HTTPException(404, "Item não encontrado")

    if video.download_status != DownloadStatus.DONE or not video.storage_path:
        raise HTTPException(409, "Item ainda não foi baixado")

    storage_root = Path(settings.storage_dir).resolve()
    file_path = (storage_root / video.storage_path).resolve()
    if storage_root not in file_path.parents and file_path != storage_root:
        raise HTTPException(400, "Caminho inválido")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "Arquivo não encontrado")

    filename = getattr(video, "original_filename", None) or file_path.name
    content_type = getattr(video, "mime_type", None)
    if not content_type and filename:
        content_type = mimetypes.guess_type(filename)[0]
    content_type = content_type or "application/octet-stream"
    disposition = f'attachment; filename="{filename}"'
    return _range_stream_response(file_path, request, media_type=content_type, content_disposition=disposition)


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Redirect 302 para o stream local com token. Mantido para acesso direto
    autenticado (curl, ferramentas externas). O frontend usa /stream-url.
    """
    video = await VideoRepository(db).get_by_id(video_id)
    if video is None:
        raise HTTPException(404, "Vídeo não encontrado")

    if video.download_status != DownloadStatus.DONE or not video.storage_path:
        raise HTTPException(409, "Vídeo ainda não foi baixado")

    if (getattr(video, "media_type", "video") or "video").lower() != "video":
        raise HTTPException(409, "Este item não é um vídeo")

    token = _make_stream_token(video_id, 3600)
    return RedirectResponse(f"/api/videos/{video_id}/stream-local?token={token}", status_code=302)


@router.get("/{video_id}/progress", response_model=ProgressOut)
async def get_video_progress(
    video_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await progress_svc.get_progress(user_id, video_id, db)


@router.post("/{video_id}/progress", response_model=ProgressOut)
async def save_video_progress(
    video_id: int,
    data: ProgressIn,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await progress_svc.save_progress(
            user_id=user_id,
            video_id=video_id,
            progress_seconds=data.progress_seconds,
            completed=data.completed,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except IntegrityError:
        raise HTTPException(401, "Sessão inválida. Faça login novamente.")
