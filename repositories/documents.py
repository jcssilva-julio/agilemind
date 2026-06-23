"""Repositório de documentos (`documents`) — metadados, dono e visibilidade."""
from __future__ import annotations

from typing import Optional, Protocol


class DocumentsRepo(Protocol):
    def create(self, owner_user_id: str, alias: str, filename: str,
               storage_path: str, visibility: str) -> str: ...
    def get(self, doc_id: str) -> Optional[dict]: ...
    def delete(self, doc_id: str) -> None: ...
    def set_visibility(self, doc_id: str, visibility: str) -> None: ...
    def list_visible_for(self, user_id: str) -> list[dict]: ...
    def count_by_owner(self, user_id: str) -> int: ...


class SupabaseDocumentsRepo:
    def __init__(self, client):
        self._sb = client

    def create(self, owner_user_id, alias, filename, storage_path, visibility) -> str:
        res = self._sb.table("documents").insert({
            "owner_user_id": owner_user_id, "alias": alias, "filename": filename,
            "storage_path": storage_path, "visibility": visibility,
        }).execute()
        return res.data[0]["id"]

    def get(self, doc_id) -> Optional[dict]:
        res = self._sb.table("documents").select("*").eq("id", doc_id).limit(1).execute()
        return res.data[0] if res.data else None

    def delete(self, doc_id) -> None:
        self._sb.table("documents").delete().eq("id", doc_id).execute()

    def set_visibility(self, doc_id, visibility) -> None:
        self._sb.table("documents").update({"visibility": visibility}).eq("id", doc_id).execute()

    def list_visible_for(self, user_id) -> list[dict]:
        # Próprios (qualquer visibilidade) + públicos de qualquer dono.
        res = self._sb.table("documents").select("*").or_(
            f"owner_user_id.eq.{user_id},visibility.eq.public"
        ).order("created_at", desc=True).execute()
        return res.data or []

    def count_by_owner(self, user_id) -> int:
        res = (self._sb.table("documents").select("id", count="exact")
               .eq("owner_user_id", user_id).execute())
        return res.count or 0

    def list_all(self) -> list[dict]:
        res = self._sb.table("documents").select("*").order("created_at", desc=True).execute()
        return res.data or []
