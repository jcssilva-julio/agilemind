"""
Abstração do provedor de identidade (Supabase Auth).

Mantém o resto do código desacoplado do Supabase: nos testes injetamos um fake
em memória (sem rede). A implementação real usa a Admin API (service_role) para
criar/remover usuários e o sign_in para verificar credenciais.
"""
from __future__ import annotations

from typing import Protocol

from .errors import Conflict, Unauthorized


class AuthProvider(Protocol):
    def create_user(self, email: str, password: str) -> str:
        """Cria o usuário e retorna o id. Levanta Conflict se o e-mail já existe."""
        ...

    def delete_user(self, user_id: str) -> None:
        ...

    def authenticate(self, email: str, password: str) -> str:
        """Retorna o user_id se as credenciais batem; senão levanta Unauthorized."""
        ...

    def find_user_id(self, email: str) -> str | None:
        """user_id pelo e-mail, ou None se não existe."""
        ...

    def get_email(self, user_id: str) -> str | None: ...
    def update_password(self, user_id: str, new_password: str) -> None: ...
    def update_email(self, user_id: str, new_email: str) -> None: ...
    def list_users(self) -> list[dict]:
        """Lista [{id, email}] de todos os usuários do Auth."""
        ...


class SupabaseAuthProvider:
    def __init__(self, client, url: str, key: str):
        # Cliente admin (service_role) — usado só para operações privilegiadas.
        self._sb = client
        # url/key para abrir clientes descartáveis na verificação de senha,
        # sem contaminar o estado de auth do cliente admin compartilhado.
        self._url = url
        self._key = key

    def create_user(self, email: str, password: str) -> str:
        try:
            res = self._sb.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
            return res.user.id
        except Exception as e:  # supabase levanta AuthApiError em duplicidade
            if "already" in str(e).lower() or "exists" in str(e).lower():
                raise Conflict()
            raise

    def delete_user(self, user_id: str) -> None:
        self._sb.auth.admin.delete_user(user_id)

    def authenticate(self, email: str, password: str) -> str:
        # Cliente descartável: o sign_in muta o estado de auth do cliente, então
        # nunca usamos o cliente admin aqui (senão ele perde a service_role).
        from supabase import create_client

        verifier = create_client(self._url, self._key)
        try:
            res = verifier.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception:
            raise Unauthorized()
        finally:
            try:
                verifier.auth.sign_out()
            except Exception:
                pass
        if not res or not getattr(res, "user", None):
            raise Unauthorized()
        return res.user.id

    def find_user_id(self, email: str) -> str | None:
        email = email.strip().lower()
        for u in self._raw_users():
            if (getattr(u, "email", "") or "").lower() == email:
                return u.id
        return None

    def _raw_users(self):
        try:
            return self._sb.auth.admin.list_users()
        except Exception:
            return []

    def get_email(self, user_id: str) -> str | None:
        try:
            res = self._sb.auth.admin.get_user_by_id(user_id)
            return getattr(res.user, "email", None)
        except Exception:
            return None

    def update_password(self, user_id: str, new_password: str) -> None:
        self._sb.auth.admin.update_user_by_id(user_id, {"password": new_password})

    def update_email(self, user_id: str, new_email: str) -> None:
        self._sb.auth.admin.update_user_by_id(
            user_id, {"email": new_email, "email_confirm": True}
        )

    def list_users(self) -> list[dict]:
        return [{"id": u.id, "email": getattr(u, "email", None)} for u in self._raw_users()]
