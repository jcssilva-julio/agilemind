"""Trilha de auditoria administrativa (`admin_audit_log`). Somente append/leitura."""
from __future__ import annotations

from typing import Optional, Protocol


class AuditRepo(Protocol):
    def log(self, actor_user_id: Optional[str], action: str,
            target_user_id: Optional[str] = None,
            target_document_id: Optional[str] = None,
            details: Optional[dict] = None) -> None: ...
    def list(self, limit: int = 200) -> list[dict]: ...


class SupabaseAuditRepo:
    def __init__(self, client):
        self._sb = client

    def log(self, actor_user_id, action, target_user_id=None,
            target_document_id=None, details=None) -> None:
        self._sb.table("admin_audit_log").insert({
            "actor_user_id": actor_user_id,
            "action": action,
            "target_user_id": target_user_id,
            "target_document_id": target_document_id,
            "details": details,
        }).execute()

    def list(self, limit=200) -> list[dict]:
        res = (self._sb.table("admin_audit_log").select("*")
               .order("created_at", desc=True).limit(limit).execute())
        return res.data or []
