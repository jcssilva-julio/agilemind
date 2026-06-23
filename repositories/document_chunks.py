"""Repositório de chunks + embeddings (`document_chunks`)."""
from __future__ import annotations

from typing import Protocol


class DocumentChunksRepo(Protocol):
    def create_many(self, document_id: str, items: list[dict], embedding_model: str) -> None:
        """items: [{'chunk_index','content','embedding'}]"""
        ...
    def get_by_document(self, document_id: str) -> list[dict]: ...
    def delete_by_document(self, document_id: str) -> None: ...


class SupabaseDocumentChunksRepo:
    def __init__(self, client):
        self._sb = client

    def create_many(self, document_id, items, embedding_model) -> None:
        rows = [{
            "document_id": document_id,
            "chunk_index": it["chunk_index"],
            "content": it["content"],
            "embedding": it["embedding"],
            "embedding_model": embedding_model,
        } for it in items]
        # Insere em lotes para não estourar limites de payload.
        for i in range(0, len(rows), 200):
            self._sb.table("document_chunks").insert(rows[i:i + 200]).execute()

    def get_by_document(self, document_id) -> list[dict]:
        res = (self._sb.table("document_chunks").select("content, embedding")
               .eq("document_id", document_id).order("chunk_index").execute())
        return res.data or []

    def delete_by_document(self, document_id) -> None:
        self._sb.table("document_chunks").delete().eq("document_id", document_id).execute()
