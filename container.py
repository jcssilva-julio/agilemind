"""
Container de dependências (injeção). Em produção monta os adaptadores reais a
partir do cliente Supabase; nos testes recebe fakes em memória, sem rede.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from auth.rate_limiter import LoginRateLimiter
from auth.service import AuthService
from config import Config


@dataclass
class Container:
    config: Config
    auth_provider: Any
    profiles: Any
    sessions: Any
    auth_service: AuthService


def build_container(config: Config | None = None) -> Container:
    """Monta o container real (Supabase). Usado pela aplicação em execução."""
    from supabase import create_client

    from repositories.profiles import SupabaseProfilesRepo
    from repositories.sessions import SupabaseSessionsRepo
    from services.auth_provider import SupabaseAuthProvider

    config = config or Config()
    config.require_supabase()
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    auth_provider = SupabaseAuthProvider(sb, config.SUPABASE_URL, config.SUPABASE_KEY)
    profiles = SupabaseProfilesRepo(sb)
    sessions = SupabaseSessionsRepo(sb)
    return _assemble(config, auth_provider, profiles, sessions)


def _assemble(config, auth_provider, profiles, sessions) -> Container:
    rate_limiter = LoginRateLimiter(
        max_attempts=config.LOGIN_MAX_ATTEMPTS,
        lockout_seconds=config.LOGIN_LOCKOUT_MINUTES * 60,
    )
    auth_service = AuthService(config, auth_provider, profiles, sessions, rate_limiter)
    return Container(
        config=config,
        auth_provider=auth_provider,
        profiles=profiles,
        sessions=sessions,
        auth_service=auth_service,
    )
