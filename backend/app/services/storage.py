"""File storage abstraction.

`storage_backend` in settings selects the implementation:
- "local": files in a Docker volume (default, works out of the box)
- "s3": S3-compatible object storage (drop-in for MinIO / AWS S3 / Scaleway)

Routes never touch the filesystem directly — they call these functions, so
switching to S3 later requires only implementing S3Storage (and setting
STORAGE_BACKEND=s3 plus S3_* variables).
"""
import shutil
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


class LocalStorage:
    def __init__(self, base_path: str):
        self.base = Path(base_path)

    def save(self, category: str, filename_hint: str, content: bytes) -> tuple[str, str]:
        """Store file, return (stored_path, stored_name)."""
        directory = self.base / category
        directory.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename_hint).suffix.lower()
        stored_name = f"{uuid4().hex}{suffix}"
        dest = directory / stored_name
        dest.write_bytes(content)
        return str(dest), stored_name

    def exists(self, stored_path: str) -> bool:
        return Path(stored_path).is_file()

    def delete(self, stored_path: str | None) -> None:
        if not stored_path:
            return
        path = Path(stored_path)
        if path.is_file() and str(path).startswith(str(self.base)):
            path.unlink(missing_ok=True)

    def read(self, stored_path: str) -> bytes:
        return Path(stored_path).read_bytes()


class S3Storage:
    """Placeholder: implement with boto3 when moving to object storage."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "S3 storage is not implemented yet. Set STORAGE_BACKEND=local."
        )


def get_storage():
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(settings.storage_local_path)


storage = get_storage()
