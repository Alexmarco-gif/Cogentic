"""Object storage helpers for production document and model artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

class S3Object(NamedTuple):
    bucket: str
    key: str


def parse_s3_path(storage_path: str) -> S3Object | None:
    """Parse supported S3 object URL forms."""
    parsed = urlparse(storage_path)

    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        return S3Object(bucket, key) if bucket and key else None

    if parsed.scheme in {"http", "https"}:
        host = (parsed.netloc or "").lower()
        path = parsed.path.lstrip("/")

        if host == "s3.amazonaws.com":
            bucket, _, key = path.partition("/")
            return S3Object(bucket, key) if bucket and key else None

        if host.endswith(".s3.amazonaws.com"):
            bucket = host[: -len(".s3.amazonaws.com")]
            return S3Object(bucket, path) if bucket and path else None

        if ".s3." in host and host.endswith(".amazonaws.com"):
            bucket, _, _region_host = host.partition(".s3.")
            return S3Object(bucket, path) if bucket and path else None

    return None


def _s3_client():
    try:
        import boto3  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover - production dependency
        raise RuntimeError("boto3 is not installed") from exc

    return boto3.client("s3")


def download_s3_object(storage_path: str) -> bytes:
    obj = parse_s3_path(storage_path)
    if obj is None:
        raise ValueError(f"Unsupported S3 path: {storage_path}")

    client = _s3_client()
    response = client.get_object(Bucket=obj.bucket, Key=obj.key)
    return response["Body"].read()


def delete_s3_object(storage_path: str) -> bool:
    obj = parse_s3_path(storage_path)
    if obj is None:
        return False

    client = _s3_client()
    from botocore.exceptions import ClientError  # type: ignore[import]

    try:
        client.head_object(Bucket=obj.bucket, Key=obj.key)
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code == 404:
            return False
        raise

    client.delete_object(Bucket=obj.bucket, Key=obj.key)
    return True


def storage_path_is_object(storage_path: str) -> bool:
    return parse_s3_path(storage_path) is not None


def download_storage_object(storage_path: str) -> bytes:
    obj = parse_s3_path(storage_path)
    if obj is None:
        raise ValueError(f"Unsupported object storage path: {storage_path}")
    return download_s3_object(storage_path)


def delete_storage_object(storage_path: str) -> bool:
    if parse_s3_path(storage_path) is None:
        return False
    return delete_s3_object(storage_path)


def local_path_from_storage_path(storage_path: str) -> Path:
    parsed = urlparse(storage_path)
    return Path(parsed.path) if parsed.scheme == "file" else Path(storage_path)
