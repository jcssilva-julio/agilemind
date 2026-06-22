"""Parâmetros editáveis em runtime (`app_config`), ex.: modelo de IA."""
from __future__ import annotations

from typing import Optional, Protocol


class AppConfigRepo(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str, updated_by: Optional[str] = None) -> None: ...


class SupabaseAppConfigRepo:
    def __init__(self, client):
        self._sb = client

    def get(self, key) -> Optional[str]:
        res = self._sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        return res.data[0]["value"] if res.data else None

    def set(self, key, value, updated_by=None) -> None:
        self._sb.table("app_config").upsert({
            "key": key, "value": value, "updated_by": updated_by,
        }).execute()
