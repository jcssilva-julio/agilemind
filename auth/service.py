"""
Regras de negócio de autenticação: criação/desativação via senha master, login
(com rate limit e checagem de conta ativa) e gestão de sessão server-side.

Não conhece Flask nem Supabase diretamente — recebe provider/repos por injeção.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from services.errors import Conflict, RateLimited, Unauthorized, ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    def __init__(self, config, auth_provider, profiles, sessions, rate_limiter):
        self.cfg = config
        self.provider = auth_provider
        self.profiles = profiles
        self.sessions = sessions
        self.rate_limiter = rate_limiter

    # ── Admin (exige senha master) ──────────────────────────────────────
    def _check_master(self, master_password) -> None:
        # Ausente = requisição malformada (400, AUTH-03); presente e errada = 401 (AUTH-02).
        if master_password is None or master_password == "":
            raise ValidationError("Senha master obrigatória")
        expected = self.cfg.MASTER_PASSWORD or ""
        # Comparação em tempo constante; mensagem genérica.
        if not secrets.compare_digest(str(master_password), expected):
            raise Unauthorized()

    def create_user(self, master_password, email, password, nome) -> str:
        self._check_master(master_password)
        email = (email or "").strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValidationError("E-mail inválido")
        if not password or len(password) < self.cfg.MIN_PASSWORD_LEN:
            raise ValidationError(
                f"A senha deve ter ao menos {self.cfg.MIN_PASSWORD_LEN} caracteres"
            )
        user_id = self.provider.create_user(email, password)  # Conflict se duplicado
        self.profiles.create(user_id, (nome or "").strip())
        return user_id

    def deactivate_user(self, master_password, email) -> None:
        self._check_master(master_password)
        email = (email or "").strip().lower()
        user_id = self.provider.find_user_id(email)
        if not user_id:
            # Não revela existência; trata como ok silencioso.
            return
        self.profiles.set_active(user_id, False)

    # ── Login / sessão ──────────────────────────────────────────────────
    def login(self, email, password) -> str:
        email = (email or "").strip().lower()
        if not email or not password:
            raise ValidationError("Informe e-mail e senha")
        if self.rate_limiter.is_locked(email):
            raise RateLimited()
        try:
            user_id = self.provider.authenticate(email, password)
        except Unauthorized:
            self.rate_limiter.register_failure(email)
            raise
        if not self.profiles.is_active(user_id):  # AUTH-26
            self.rate_limiter.register_failure(email)
            raise Unauthorized()
        self.rate_limiter.reset(email)
        return self._open_session(user_id)

    def _open_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=self.cfg.SESSION_TTL_HOURS)
        self.sessions.create(token, user_id, expires)
        return token

    def logout(self, token: str) -> None:
        if token:
            self.sessions.delete(token)

    def resolve(self, token: str):
        """user_id da sessão válida, ou None."""
        if not token:
            return None
        return self.sessions.get_user_id(token)
