"""
Repositório de sessões server-side (tabela `sessions`).

Guardar a sessão no servidor permite invalidação real no logout (AUTH-23) e
expiração efetiva (AUTH-22) — algo que um cookie assinado stateless não garante.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionsRepo(Protocol):
    def create(self, token: str, user_id: str, expires_at: datetime) -> None: ...
    def get_user_id(self, token: str) -> Optional[str]:
        """Retorna user_id se a sessão existe e não expirou; senão None."""
        ...
    def delete(self, token: str) -> None: ...


class SupabaseSessionsRepo:
    def __init__(self, client):
        self._sb = client

    def create(self, token: str, user_id: str, expires_at: datetime) -> None:
        self._sb.table("sessions").insert(
            {
                "token": token,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
            }
        ).execute()

    def get_user_id(self, token: str) -> Optional[str]:
        res = (
            self._sb.table("sessions")
            .select("user_id, expires_at")
            .eq("token", token)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        row = res.data[0]
        expires = datetime.fromisoformat(row["expires_at"])
        if expires <= _now():
            self.delete(token)
            return None
        return row["user_id"]

    def delete(self, token: str) -> None:
        self._sb.table("sessions").delete().eq("token", token).execute()
