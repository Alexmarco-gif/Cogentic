"""Object storage helpers for production document and model artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

from backend.config import get_settings


class GcsObject(NamedTuple):
    bucket: str
    name: str


def parse_gcs_path(storage_path: str) -> GcsObject | None:
    """Parse supported Cloud Storage object URL forms."""
    parsed = urlparse(storage_path)

    if parsed.scheme == "gs":
        bucket = parsed.netloc
        name = parsed.path.lstrip("/")
        return GcsObject(bucket, name) if bucket and name else None

    if parsed.scheme in {"http", "https"}:
        host = (parsed.netloc or "").lower()
        path = parsed.path.lstrip("/")

        if host == "storage.googleapis.com":
            bucket, _, name = path.partition("/")
            return GcsObject(bucket, name) if bucket and name else None

        if host.endswith(".storage.googleapis.com"):
            bucket = host[: -len(".storage.googleapis.com")]
            return GcsObject(bucket, path) if bucket and path else None

    return None


def _gcs_client():
    try:
        from google.cloud import storage  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover - production dependency
        raise RuntimeError("google-cloud-storage is not installed") from exc

    settings = get_settings()
    if settings.google_cloud_project:
        return storage.Client(project=settings.google_cloud_project)
    return storage.Client()


def download_gcs_object(storage_path: str) -> bytes:
    obj = parse_gcs_path(storage_path)
    if obj is None:
        raise ValueError(f"Unsupported Cloud Storage path: {storage_path}")

    client = _gcs_client()
    return client.bucket(obj.bucket).blob(obj.name).download_as_bytes()


def delete_gcs_object(storage_path: str) -> bool:
    obj = parse_gcs_path(storage_path)
    if obj is None:
        return False

    client = _gcs_client()
    blob = client.bucket(obj.bucket).blob(obj.name)
    if not blob.exists():
        return False
    blob.delete()
    return True


def local_path_from_storage_path(storage_path: str) -> Path:
    parsed = urlparse(storage_path)
    return Path(parsed.path) if parsed.scheme == "file" else Path(storage_path)
