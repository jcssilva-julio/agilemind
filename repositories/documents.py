"""
Repositório de documentos (`documents`). Por enquanto só o necessário para a
camada de administração (contagem por dono, p/ a regra de exclusão ADM-26).
A migração completa do upload entra nas Fases 3/4.
"""
from __future__ import annotations

from typing import Protocol


class DocumentsRepo(Protocol):
    def count_by_owner(self, user_id: str) -> int: ...


class SupabaseDocumentsRepo:
    def __init__(self, client):
        self._sb = client

    def count_by_owner(self, user_id) -> int:
        res = (self._sb.table("documents").select("id", count="exact")
               .eq("owner_user_id", user_id).execute())
        return res.count or 0
