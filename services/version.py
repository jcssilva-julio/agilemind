"""
Informações de versão do build em execução. No Railway, o commit vem das
variáveis RAILWAY_GIT_* injetadas no deploy; localmente, cai para o git local.
`started_at` mostra quando o processo atual subiu (útil para saber se o deploy
mais recente já está no ar).
"""
import os
import subprocess
from datetime import datetime, timezone

_STARTED_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return None


def get_version_info() -> dict:
    sha = os.getenv("RAILWAY_GIT_COMMIT_SHA") or _git_sha() or ""
    return {
        "commit": sha[:7] if sha else "dev",
        "commit_full": sha or None,
        "message": os.getenv("RAILWAY_GIT_COMMIT_MESSAGE"),
        "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID"),
        "started_at": _STARTED_AT,
    }
