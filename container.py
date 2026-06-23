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
    chunks: Any
    storage: Any
    ai: Any
    auth_service: AuthService
    admin_service: AdminService


def models_getter(app_config, config):
    def _get():
        return {
            "claude_model": app_config.get("claude_model") or config.DEFAULT_CLAUDE_MODEL,
            "voyage_model": app_config.get("voyage_model") or config.DEFAULT_VOYAGE_MODEL,
        }
    return _get


def build_container(config: Config | None = None) -> Container:
    """Monta o container real (Supabase). Usado pela aplicação em execução."""
    from supabase import create_client

    from repositories.app_config import SupabaseAppConfigRepo
    from repositories.audit import SupabaseAuditRepo
    from repositories.document_chunks import SupabaseDocumentChunksRepo
    from repositories.documents import SupabaseDocumentsRepo
    from repositories.profiles import SupabaseProfilesRepo
    from repositories.sessions import SupabaseSessionsRepo
    from services.ai import AIService
    from services.auth_provider import SupabaseAuthProvider
    from services.model_validator import RealModelValidator
    from services.storage import StorageService

    config = config or Config()
    config.require_supabase()
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    app_config = SupabaseAppConfigRepo(sb)

    return _assemble(
        config,
        auth_provider=SupabaseAuthProvider(sb, config.SUPABASE_URL, config.SUPABASE_KEY),
        profiles=SupabaseProfilesRepo(sb),
        sessions=SupabaseSessionsRepo(sb),
        audit=SupabaseAuditRepo(sb),
        app_config=app_config,
        documents=SupabaseDocumentsRepo(sb),
        chunks=SupabaseDocumentChunksRepo(sb),
        storage=StorageService(sb, config.STORAGE_BUCKET),
        ai=AIService(config.ANTHROPIC_API_KEY, config.VOYAGE_API_KEY, models_getter(app_config, config)),
        model_validator=RealModelValidator(config.ANTHROPIC_API_KEY, config.VOYAGE_API_KEY),
    )


def _assemble(config, auth_provider, profiles, sessions, audit, app_config,
              documents, chunks, storage, ai, model_validator) -> Container:
    rate_limiter = LoginRateLimiter(
        max_attempts=config.LOGIN_MAX_ATTEMPTS,
        lockout_seconds=config.LOGIN_LOCKOUT_MINUTES * 60,
    )
    auth_service = AuthService(config, auth_provider, profiles, sessions, rate_limiter)
    admin_service = AdminService(
        config, auth_provider, profiles, sessions, audit, documents,
        app_config, model_validator, chunks=chunks, storage=storage, ai=ai,
    )
    return Container(
        config=config, auth_provider=auth_provider, profiles=profiles,
        sessions=sessions, audit=audit, app_config=app_config, documents=documents,
        chunks=chunks, storage=storage, ai=ai,
        auth_service=auth_service, admin_service=admin_service,
    )
