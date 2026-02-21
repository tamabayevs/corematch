"""
CoreMatch — Storage Service
Pluggable adapter: local (dev) or Cloudflare R2 (prod).
Provider selected via STORAGE_PROVIDER env var: 'local' | 'r2'
"""
import os
import io
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────

class StorageService(ABC):
    @abstractmethod
    def upload_file(self, file_obj: io.IOBase, key: str, content_type: str = "video/mp4") -> str:
        """Upload file. Returns public or signed URL."""

    @abstractmethod
    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for temporary access. expires_in in seconds."""

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """Delete a file from storage."""

    @abstractmethod
    def download_file(self, key: str) -> bytes:
        """Download a file as bytes."""


# ──────────────────────────────────────────────────────────────
# Local Storage (development only)
# ──────────────────────────────────────────────────────────────

class LocalStorageService(StorageService):
    """Stores files on local disk. For development only."""

    def __init__(self, base_path: str = "/app/uploads"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        # Sanitize key to prevent path traversal
        safe_key = key.replace("..", "").lstrip("/")
        full_path = os.path.join(self.base_path, safe_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def upload_file(self, file_obj: io.IOBase, key: str, content_type: str = "video/mp4") -> str:
        path = self._key_to_path(key)
        with open(path, "wb") as f:
            if hasattr(file_obj, "read"):
                f.write(file_obj.read())
            else:
                f.write(file_obj)
        logger.debug("Local upload: %s", path)
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:5000")
        return f"{backend_url}/uploads/{key}"

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:5000")
        return f"{backend_url}/uploads/{key}"

    def delete_file(self, key: str) -> None:
        path = self._key_to_path(key)
        if os.path.exists(path):
            os.remove(path)
            logger.debug("Local delete: %s", path)

    def download_file(self, key: str) -> bytes:
        path = self._key_to_path(key)
        with open(path, "rb") as f:
            return f.read()


# ──────────────────────────────────────────────────────────────
# Cloudflare R2 Storage (production)
# R2 is S3-compatible — uses boto3
# ──────────────────────────────────────────────────────────────

class R2StorageService(StorageService):
    """Cloudflare R2 via S3-compatible API."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
        access_key = os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"]
        secret_key = os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"]
        self.bucket = os.environ["CLOUDFLARE_R2_BUCKET_NAME"]
        self.public_url = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "").rstrip("/")

        endpoint = os.environ.get(
            "CLOUDFLARE_R2_ENDPOINT",
            f"https://{account_id}.r2.cloudflarestorage.com"
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )

    def upload_file(self, file_obj: io.IOBase, key: str, content_type: str = "video/mp4") -> str:
        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "private, max-age=3600",
            },
        )
        logger.info("R2 upload: %s", key)
        return f"{self.public_url}/{key}" if self.public_url else key

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    def delete_file(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
        logger.info("R2 delete: %s", key)

    def download_file(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()


# ──────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────

_storage_instance = None


def get_storage_service() -> StorageService:
    """Return cached storage service instance."""
    global _storage_instance
    if _storage_instance is None:
        provider = os.environ.get("STORAGE_PROVIDER", "local").lower()
        if provider == "r2":
            _storage_instance = R2StorageService()
            logger.info("Storage provider: Cloudflare R2")
        else:
            upload_dir = os.environ.get("LOCAL_UPLOAD_DIR", "/app/uploads")
            _storage_instance = LocalStorageService(upload_dir)
            logger.info("Storage provider: local (%s)", upload_dir)
    return _storage_instance
