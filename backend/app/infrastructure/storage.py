import logging
import os
import errno
import shutil
from pathlib import Path
import boto3
from botocore.config import Config
from app.config import settings

logger = logging.getLogger(__name__)

_s3_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    _s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path",
                "payload_signing_enabled": False,
            },
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return _s3_client

def _is_local_backend() -> bool:
    return (settings.storage_backend or "s3").lower() == "local"

def upload(local_path: Path, key: str) -> str:
    """
    Uploads a local file to S3 and returns the storage key.
    """
    if _is_local_backend():
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

    logger.info(f"Uploading {local_path} to S3 {settings.s3_bucket}/{key}")
    client = _get_s3_client()
    client.upload_file(str(local_path), settings.s3_bucket, key)
    return key

def presigned_url(
    key: str,
    expires: int = 3600,
    response_content_type: str | None = None,
    response_content_disposition: str | None = None,
) -> str:
    """
    Generates a presigned URL for downloading a file.
    """
    client = _get_s3_client()
    params = {"Bucket": settings.s3_bucket, "Key": key}
    if response_content_type:
        params["ResponseContentType"] = response_content_type
    if response_content_disposition:
        params["ResponseContentDisposition"] = response_content_disposition
    url = client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires
    )
    return url

def delete(key: str) -> None:
    """
    Deletes an object from S3.
    """
    if _is_local_backend():
        storage_root = Path(settings.storage_dir)
        target = storage_root / key
        try:
            target.unlink(missing_ok=True)
        except TypeError:
            if target.exists():
                target.unlink()
        return

    logger.info(f"Deleting S3 object {settings.s3_bucket}/{key}")
    client = _get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket, Key=key)

def storage_used_bytes() -> int:
    """
    Paginates all objects in the bucket and sums their sizes.
    """
    if _is_local_backend():
        storage_root = Path(settings.storage_dir)
        if not storage_root.exists():
            return 0
        total_bytes = 0
        for p in storage_root.rglob("*"):
            if p.is_file():
                try:
                    total_bytes += p.stat().st_size
                except OSError:
                    pass
        return total_bytes

    total_bytes = 0
    try:
        client = _get_s3_client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.s3_bucket):
            for obj in page.get("Contents", []):
                total_bytes += obj.get("Size", 0)
    except Exception as e:
        logger.error(f"Error fetching storage used bytes: {e}")
    return total_bytes
