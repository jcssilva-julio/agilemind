"""
Regras de autenticação do dia a dia: login (com rate limit e conta ativa),
sessão server-side e troca de senha pelo próprio usuário.

A criação/gestão de usuários NÃO está aqui — fica na camada de administração
(AdminService), feita por um admin autenticado. A senha master só aparece no
bootstrap/emergência.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from services.errors import Unauthorized, ValidationError
from services.passwords import validate_strength
from services.validation import normalize_email


class AuthService:
    def __init__(self, config, auth_provider, profiles, sessions, rate_limiter):
        self.cfg = config
        self.provider = auth_provider
        self.profiles = profiles
        self.sessions = sessions
        self.rate_limiter = rate_limiter

    # ── Login / sessão ──────────────────────────────────────────────────
    def login(self, email, password) -> str:
        email = normalize_email(email)
        if not email or not password:
            raise ValidationError("Informe e-mail e senha")
        if self.rate_limiter.is_locked(email):
            from services.errors import RateLimited
            raise RateLimited()
        try:
            user_id = self.provider.authenticate(email, password)
        except Unauthorized:
            self.rate_limiter.register_failure(email)
            raise
        if not self.profiles.is_active(user_id):  # AUTH-26 / ADM-24
            self.rate_limiter.register_failure(email)
            raise Unauthorized()
        self.rate_limiter.reset(email)
        return self.open_session(user_id)

    def open_session(self, user_id: str) -> str:
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

    # ── Troca de senha pelo próprio usuário (UC-08 / ADM-37..44) ────────
    def change_password(self, user_id, current, new, confirm) -> None:
        # Validações locais ANTES de qualquer chamada ao Supabase (ADM-39).
        if new != confirm:
            raise ValidationError("A nova senha e a confirmação não coincidem")
        if current and new == current:
            raise ValidationError("A nova senha deve ser diferente da atual")  # ADM-40
        validate_strength(new, self.cfg.MIN_PASSWORD_LEN)  # ADM-41

        email = self.provider.get_email(user_id)
        if not email:
            raise Unauthorized()
        # Verifica a senha atual (ADM-38).
        try:
            self.provider.authenticate(email, current)
        except Unauthorized:
            raise Unauthorized()

        self.provider.update_password(user_id, new)
        self.sessions.delete_by_user(user_id)  # invalida todas as sessões (ADM-42)
