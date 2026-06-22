"""
Configuração central do AgileMind.

Lê tudo de variáveis de ambiente (Railway/.env), nunca hardcoded. Aceita
overrides no construtor para testes (config determinística, sem rede).
"""
import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class Config:
    # APIs externas
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    VOYAGE_API_KEY: str = field(default_factory=lambda: _env("VOYAGE_API_KEY"))

    # Supabase
    SUPABASE_URL: str = field(default_factory=lambda: _env("SUPABASE_URL"))
    SUPABASE_KEY: str = field(default_factory=lambda: _env("SUPABASE_KEY"))
    STORAGE_BUCKET: str = "documents"

    # Segurança / sessão
    MASTER_PASSWORD: str = field(default_factory=lambda: _env("MASTER_PASSWORD"))
    FLASK_SECRET_KEY: str = field(default_factory=lambda: _env("FLASK_SECRET_KEY", "dev-insecure"))
    SESSION_COOKIE: str = "agilemind_session"
    SESSION_TTL_HOURS: int = 12

    # Regras de login (AUTH-06 / AUTH-15)
    MIN_PASSWORD_LEN: int = 6
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    def require_supabase(self) -> None:
        if not self.SUPABASE_URL or not self.SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL e SUPABASE_KEY são obrigatórias")
