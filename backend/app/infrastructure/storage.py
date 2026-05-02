import logging
import os
import errno
import shutil
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


def upload(local_path: Path, key: str) -> str:
    """Move o arquivo de `local_path` para `{storage_dir}/{key}` e devolve a key."""
    storage_root = Path(settings.storage_dir)
    dest = storage_root / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Storing {local_path} to {dest}")
    try:
        os.replace(str(local_path), str(dest))
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
        shutil.copy2(str(local_path), str(dest))
        try:
            os.unlink(str(local_path))
        except OSError:
            pass
    return key


def delete(key: str) -> None:
    storage_root = Path(settings.storage_dir)
    target = storage_root / key
    try:
        target.unlink(missing_ok=True)
    except TypeError:
        if target.exists():
            target.unlink()
