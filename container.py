"""
Container de dependências (injeção). Em produção monta os adaptadores reais a
partir do cliente Supabase; nos testes recebe fakes em memória, sem rede.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from admin.service import AdminService
from auth.rate_limiter import LoginRateLimiter
from auth.service import AuthService
from config import Config


@dataclass
class Container:
    config: Config
    auth_provider: Any
    profiles: Any
    sessions: Any
    audit: Any
    app_config: Any
    documents: Any
    auth_service: AuthService
    admin_service: AdminService


def build_container(config: Config | None = None) -> Container:
    """Monta o container real (Supabase). Usado pela aplicação em execução."""
    from supabase import create_client

    from repositories.app_config import SupabaseAppConfigRepo
    from repositories.audit import SupabaseAuditRepo
    from repositories.documents import SupabaseDocumentsRepo
    from repositories.profiles import SupabaseProfilesRepo
    from repositories.sessions import SupabaseSessionsRepo
    from services.auth_provider import SupabaseAuthProvider
    from services.model_validator import RealModelValidator

    config = config or Config()
    config.require_supabase()
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    return _assemble(
        config,
        auth_provider=SupabaseAuthProvider(sb, config.SUPABASE_URL, config.SUPABASE_KEY),
        profiles=SupabaseProfilesRepo(sb),
        sessions=SupabaseSessionsRepo(sb),
        audit=SupabaseAuditRepo(sb),
        app_config=SupabaseAppConfigRepo(sb),
        documents=SupabaseDocumentsRepo(sb),
        model_validator=RealModelValidator(config.ANTHROPIC_API_KEY, config.VOYAGE_API_KEY),
    )


def _assemble(config, auth_provider, profiles, sessions, audit, app_config,
              documents, model_validator) -> Container:
    rate_limiter = LoginRateLimiter(
        max_attempts=config.LOGIN_MAX_ATTEMPTS,
        lockout_seconds=config.LOGIN_LOCKOUT_MINUTES * 60,
    )
    auth_service = AuthService(config, auth_provider, profiles, sessions, rate_limiter)
    admin_service = AdminService(
        config, auth_provider, profiles, sessions, audit, documents,
        app_config, model_validator,
    )
    return Container(
        config=config,
        auth_provider=auth_provider,
        profiles=profiles,
        sessions=sessions,
        audit=audit,
        app_config=app_config,
        documents=documents,
        auth_service=auth_service,
        admin_service=admin_service,
    )
