"""
GCS Storage — Google Cloud Storage client and upload helpers.

The GCS client is synchronous (google-cloud-storage). All blocking calls
are offloaded to a thread pool via asyncio.run_in_executor so FastAPI's
event loop is never blocked.

Blob naming convention:
    items/{workspace_id}/{persona_id}/{item_id}_{persona_id}_{workspace_id}.{ext}

This gives a fixed, deterministic path per item — re-uploading overwrites
the same blob, keeping storage bounded to one file per item.

Authentication:
    - If GCS_CREDENTIALS_PATH is set → load service account JSON from that path
    - Otherwise → Application Default Credentials (ADC), works on Cloud Run / GKE
"""

import asyncio
import logging
import mimetypes
import os
from functools import lru_cache
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

from src.config.Settings import settings
from src.core.Exceptions import BadRequestError, InternalError

logger = logging.getLogger(__name__)

# Allowed image MIME types
_ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
})

# Max upload size: 5 MB
_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

# Extension map for deterministic file naming
_MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


@lru_cache(maxsize=1)
def _get_gcs_client() -> storage.Client:
    """Return a cached GCS client. Created once per process."""
    if settings.GCS_CREDENTIALS_PATH:
        credentials = service_account.Credentials.from_service_account_file(
            settings.GCS_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        logger.info("gcs.client.init credentials=service_account path=%s", settings.GCS_CREDENTIALS_PATH)
        return storage.Client(credentials=credentials)

    logger.info("gcs.client.init credentials=ADC")
    return storage.Client()


def _build_blob_name(
    workspace_id: int,
    persona_id: int,
    item_id: int,
    mime_type: str,
) -> str:
    """
    Build a deterministic GCS blob path for an item image.
    Pattern: items/{workspace_id}/{persona_id}/{item_id}_{persona_id}_{workspace_id}.{ext}
    """
    ext = _MIME_TO_EXT.get(mime_type, "jpg")
    return f"items/{workspace_id}/{persona_id}/{item_id}_{persona_id}_{workspace_id}.{ext}"


def _upload_blob_sync(
    blob_name: str,
    data: bytes,
    mime_type: str,
) -> str:
    """
    Synchronous GCS upload. Runs in a thread pool — do not call directly from async code.
    Returns the public URL of the uploaded blob.
    """
    if not settings.GCS_BUCKET_NAME:
        raise InternalError("GCS_BUCKET_NAME is not configured")

    client = _get_gcs_client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(data, content_type=mime_type)

    # Return the public HTTPS URL
    url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{blob_name}"
    logger.info(
        "gcs.upload.success blob=%s size_bytes=%s mime=%s url=%s",
        blob_name, len(data), mime_type, url,
    )
    return url


async def upload_persona_logo(
    workspace_id: int,
    persona_id: int,
    file_data: bytes,
    content_type: Optional[str],
) -> str:
    """
    Validate and upload a persona logo to GCS asynchronously.

    Blob path: personas/{workspace_id}/{persona_id}_logo.{ext}
    Re-uploading overwrites the same blob.
    """
    if len(file_data) > _MAX_FILE_SIZE_BYTES:
        raise BadRequestError(
            f"Logo exceeds maximum allowed size of {_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
        )

    mime_type = content_type or "application/octet-stream"
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise BadRequestError(
            f"Unsupported image type '{mime_type}'. "
            f"Allowed: {', '.join(sorted(_ALLOWED_MIME_TYPES))}"
        )

    ext = _MIME_TO_EXT.get(mime_type, "jpg")
    blob_name = f"personas/{workspace_id}/{persona_id}_logo.{ext}"

    logger.info(
        "gcs.upload.persona_logo.start workspace_id=%s persona_id=%s "
        "blob=%s size_bytes=%s mime=%s",
        workspace_id, persona_id, blob_name, len(file_data), mime_type,
    )

    try:
        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(
            None, _upload_blob_sync, blob_name, file_data, mime_type,
        )
    except InternalError:
        raise
    except Exception as exc:
        logger.error(
            "gcs.upload.persona_logo.failed workspace_id=%s persona_id=%s error=%s",
            workspace_id, persona_id, str(exc), exc_info=True,
        )
        raise InternalError("Logo upload failed. Please try again.") from exc

    return url


async def upload_item_image(
    workspace_id: int,
    persona_id: int,
    item_id: int,
    file_data: bytes,
    content_type: Optional[str],
) -> str:
    """
    Validate and upload an item image to GCS asynchronously.

    - Validates MIME type and file size
    - Builds a deterministic blob path (overwrites existing image)
    - Runs the blocking GCS upload in a thread pool
    - Returns the public URL

    Raises
    ------
    BadRequestError
        If the file type is not allowed or the file exceeds the size limit.
    InternalError
        If GCS_BUCKET_NAME is not set or the upload fails.
    """
    # Validate size
    if len(file_data) > _MAX_FILE_SIZE_BYTES:
        raise BadRequestError(
            f"Image exceeds maximum allowed size of {_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
        )

    # Validate MIME type
    mime_type = content_type or "application/octet-stream"
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise BadRequestError(
            f"Unsupported image type '{mime_type}'. "
            f"Allowed: {', '.join(sorted(_ALLOWED_MIME_TYPES))}"
        )

    blob_name = _build_blob_name(workspace_id, persona_id, item_id, mime_type)

    logger.info(
        "gcs.upload.start workspace_id=%s persona_id=%s item_id=%s "
        "blob=%s size_bytes=%s mime=%s",
        workspace_id, persona_id, item_id, blob_name, len(file_data), mime_type,
    )

    try:
        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(
            None,
            _upload_blob_sync,
            blob_name,
            file_data,
            mime_type,
        )
    except InternalError:
        raise
    except Exception as exc:
        logger.error(
            "gcs.upload.failed workspace_id=%s persona_id=%s item_id=%s blob=%s error=%s",
            workspace_id, persona_id, item_id, blob_name, str(exc),
            exc_info=True,
        )
        raise InternalError("Image upload failed. Please try again.") from exc

    return url
