"""
Adaptadores fake em memória para os testes — mesmas interfaces dos reais, sem
rede. Permitem testar regras de negócio (auth, admin) de forma determinística.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from services.errors import Conflict, Unauthorized, ValidationError


class FakeAuthProvider:
    def __init__(self):
        self._users: dict[str, dict] = {}  # email -> {"id","password"}

    def create_user(self, email, password) -> str:
        email = email.lower()
        if email in self._users:
            raise Conflict()
        uid = str(uuid.uuid4())
        self._users[email] = {"id": uid, "password": password}
        return uid

    def delete_user(self, user_id) -> None:
        for email, u in list(self._users.items()):
            if u["id"] == user_id:
                del self._users[email]

    def authenticate(self, email, password) -> str:
        u = self._users.get(email.lower())
        if not u or u["password"] != password:
            raise Unauthorized()
        return u["id"]

    def find_user_id(self, email):
        u = self._users.get(email.lower())
        return u["id"] if u else None

    def get_email(self, user_id):
        for email, u in self._users.items():
            if u["id"] == user_id:
                return email
        return None

    def update_password(self, user_id, new_password) -> None:
        for u in self._users.values():
            if u["id"] == user_id:
                u["password"] = new_password
                return

    def update_email(self, user_id, new_email) -> None:
        for email, u in list(self._users.items()):
            if u["id"] == user_id:
                del self._users[email]
                self._users[new_email.lower()] = u
                return

    def list_users(self):
        return [{"id": u["id"], "email": email} for email, u in self._users.items()]


class FakeProfilesRepo:
    def __init__(self):
        self._p: dict[str, dict] = {}
        self._seq = 0

    def create(self, user_id, nome, role="user", created_by=None) -> None:
        self._seq += 1
        self._p[user_id] = {
            "user_id": user_id, "nome": nome, "role": role, "is_active": True,
            "created_by": created_by, "created_at": self._seq,
        }

    def get(self, user_id):
        return self._p.get(user_id)

    def get_role(self, user_id):
        p = self._p.get(user_id)
        return p["role"] if p else None

    def is_active(self, user_id):
        p = self._p.get(user_id)
        return bool(p and p["is_active"])

    def set_active(self, user_id, active):
        if user_id in self._p:
            self._p[user_id]["is_active"] = active

    def set_role(self, user_id, role):
        if user_id in self._p:
            self._p[user_id]["role"] = role

    def update_nome(self, user_id, nome):
        if user_id in self._p:
            self._p[user_id]["nome"] = nome

    def delete(self, user_id):
        self._p.pop(user_id, None)

    def list_all(self):
        return sorted(self._p.values(), key=lambda x: x["created_at"])

    def count_admins(self, only_active=True):
        return sum(
            1 for p in self._p.values()
            if p["role"] == "admin" and (p["is_active"] or not only_active)
        )

    def oldest_admin(self):
        admins = sorted(
            [p for p in self._p.values() if p["role"] == "admin"],
            key=lambda x: x["created_at"],
        )
        return admins[0] if admins else None


class FakeSessionsRepo:
    def __init__(self):
        self._s: dict[str, dict] = {}

    def create(self, token, user_id, expires_at) -> None:
        self._s[token] = {"user_id": user_id, "expires_at": expires_at}

    def get_user_id(self, token):
        row = self._s.get(token)
        if not row:
            return None
        if row["expires_at"] <= datetime.now(timezone.utc):
            del self._s[token]
            return None
        return row["user_id"]

    def delete(self, token):
        self._s.pop(token, None)

    def delete_by_user(self, user_id):
        for tok in [t for t, r in self._s.items() if r["user_id"] == user_id]:
            del self._s[tok]


class FakeAuditRepo:
    def __init__(self):
        self.entries: list[dict] = []

    def log(self, actor_user_id, action, target_user_id=None,
            target_document_id=None, details=None):
        self.entries.append({
            "actor_user_id": actor_user_id, "action": action,
            "target_user_id": target_user_id, "target_document_id": target_document_id,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def list(self, limit=200):
        return list(reversed(self.entries))[:limit]


class FakeAppConfigRepo:
    def __init__(self):
        self._c: dict[str, str] = {}

    def get(self, key):
        return self._c.get(key)

    def set(self, key, value, updated_by=None):
        self._c[key] = value


class FakeDocumentsRepo:
    def __init__(self):
        self.counts: dict[str, int] = {}

    def count_by_owner(self, user_id):
        return self.counts.get(user_id, 0)


class FakeModelValidator:
    """Rejeita ids vazios ou que contenham 'inex' (ex.: 'modelo-inexistente')."""
    def validate(self, kind, model_id):
        if kind not in ("claude", "voyage"):
            raise ValidationError("Tipo de modelo desconhecido")
        if not model_id or "inex" in model_id:
            raise ValidationError(f"Modelo '{model_id}' inválido")
