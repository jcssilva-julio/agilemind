"""Repositório de perfis (`profiles`): role, status e autoria."""
from __future__ import annotations

from typing import Optional, Protocol


class ProfilesRepo(Protocol):
    def create(self, user_id: str, nome: str, role: str = "user", created_by: Optional[str] = None) -> None: ...
    def get(self, user_id: str) -> Optional[dict]: ...
    def get_role(self, user_id: str) -> Optional[str]: ...
    def is_active(self, user_id: str) -> bool: ...
    def set_active(self, user_id: str, active: bool) -> None: ...
    def set_role(self, user_id: str, role: str) -> None: ...
    def update_nome(self, user_id: str, nome: str) -> None: ...
    def delete(self, user_id: str) -> None: ...
    def list_all(self) -> list[dict]: ...
    def count_admins(self, only_active: bool = True) -> int: ...
    def oldest_admin(self) -> Optional[dict]: ...


class SupabaseProfilesRepo:
    def __init__(self, client):
        self._sb = client

    def create(self, user_id, nome, role="user", created_by=None) -> None:
        self._sb.table("profiles").insert({
            "user_id": user_id, "nome": nome, "role": role,
            "is_active": True, "created_by": created_by,
        }).execute()

    def get(self, user_id) -> Optional[dict]:
        res = self._sb.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
        return res.data[0] if res.data else None

    def get_role(self, user_id) -> Optional[str]:
        p = self.get(user_id)
        return p["role"] if p else None

    def is_active(self, user_id) -> bool:
        p = self.get(user_id)
        return bool(p and p["is_active"])

    def set_active(self, user_id, active) -> None:
        self._sb.table("profiles").update({"is_active": active}).eq("user_id", user_id).execute()

    def set_role(self, user_id, role) -> None:
        self._sb.table("profiles").update({"role": role}).eq("user_id", user_id).execute()

    def update_nome(self, user_id, nome) -> None:
        self._sb.table("profiles").update({"nome": nome}).eq("user_id", user_id).execute()

    def delete(self, user_id) -> None:
        self._sb.table("profiles").delete().eq("user_id", user_id).execute()

    def list_all(self) -> list[dict]:
        res = self._sb.table("profiles").select("*").order("created_at").execute()
        return res.data or []

    def count_admins(self, only_active=True) -> int:
        q = self._sb.table("profiles").select("user_id", count="exact").eq("role", "admin")
        if only_active:
            q = q.eq("is_active", True)
        return q.execute().count or 0

    def oldest_admin(self) -> Optional[dict]:
        res = self._sb.table("profiles").select("*").eq("role", "admin").order("created_at").limit(1).execute()
        return res.data[0] if res.data else None
