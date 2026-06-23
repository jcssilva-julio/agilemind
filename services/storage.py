"""Storage de PDFs no Supabase Storage (bucket privado)."""
from __future__ import annotations


class StorageService:
    def __init__(self, client, bucket: str):
        self._sb = client
        self._bucket = bucket

    def upload(self, path: str, data: bytes, content_type: str = "application/pdf") -> str:
        self._sb.storage.from_(self._bucket).upload(
            path, data, {"content-type": content_type, "upsert": "true"}
        )
        return path

    def download(self, path: str) -> bytes:
        return self._sb.storage.from_(self._bucket).download(path)

    def delete(self, path: str) -> None:
        try:
            self._sb.storage.from_(self._bucket).remove([path])
        except Exception:
            pass
