"""
Adaptadores fake em memória para os testes — mesmas interfaces dos reais, sem
rede. Permitem testar regras de negócio (auth, visibilidade) de forma rápida e
determinística.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from services.errors import Conflict, Unauthorized


class FakeAuthProvider:
    def __init__(self):
        # email -> {"id", "password"}
        self._users: dict[str, dict] = {}

    def create_user(self, email: str, password: str) -> str:
        email = email.lower()
        if email in self._users:
            raise Conflict()
        uid = str(uuid.uuid4())
        self._users[email] = {"id": uid, "password": password}
        return uid

    def delete_user(self, user_id: str) -> None:
        for email, u in list(self._users.items()):
            if u["id"] == user_id:
                del self._users[email]

    def authenticate(self, email: str, password: str) -> str:
        u = self._users.get(email.lower())
        if not u or u["password"] != password:
            raise Unauthorized()
        return u["id"]

    def find_user_id(self, email: str) -> str | None:
        u = self._users.get(email.lower())
        return u["id"] if u else None


class FakeProfilesRepo:
    def __init__(self):
        self._p: dict[str, dict] = {}

    def create(self, user_id: str, nome: str) -> None:
        self._p[user_id] = {"nome": nome, "is_active": True}

    def is_active(self, user_id: str) -> bool:
        return bool(self._p.get(user_id, {}).get("is_active"))

    def set_active(self, user_id: str, active: bool) -> None:
        if user_id in self._p:
            self._p[user_id]["is_active"] = active

    def get_nome(self, user_id: str):
        return self._p.get(user_id, {}).get("nome")


class FakeSessionsRepo:
    def __init__(self):
        self._s: dict[str, dict] = {}

    def create(self, token: str, user_id: str, expires_at: datetime) -> None:
        self._s[token] = {"user_id": user_id, "expires_at": expires_at}

    def get_user_id(self, token: str):
        row = self._s.get(token)
        if not row:
            return None
        if row["expires_at"] <= datetime.now(timezone.utc):
            del self._s[token]
            return None
        return row["user_id"]

    def delete(self, token: str) -> None:
        self._s.pop(token, None)
