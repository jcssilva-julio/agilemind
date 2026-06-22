"""Repositório de perfis (tabela `profiles`). is_active controla AUTH-25/26."""
from __future__ import annotations

from typing import Optional, Protocol


class ProfilesRepo(Protocol):
    def create(self, user_id: str, nome: str) -> None: ...
    def is_active(self, user_id: str) -> bool: ...
    def set_active(self, user_id: str, active: bool) -> None: ...
    def get_nome(self, user_id: str) -> Optional[str]: ...


class SupabaseProfilesRepo:
    def __init__(self, client):
        self._sb = client

    def create(self, user_id: str, nome: str) -> None:
        self._sb.table("profiles").insert(
            {"user_id": user_id, "nome": nome, "is_active": True}
        ).execute()

    def is_active(self, user_id: str) -> bool:
        res = (
            self._sb.table("profiles")
            .select("is_active")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(res.data and res.data[0]["is_active"])

    def set_active(self, user_id: str, active: bool) -> None:
        self._sb.table("profiles").update({"is_active": active}).eq(
            "user_id", user_id
        ).execute()

    def get_nome(self, user_id: str) -> Optional[str]:
        res = (
            self._sb.table("profiles")
            .select("nome")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return res.data[0]["nome"] if res.data else None
