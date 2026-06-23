"""
Adapter de IA: embeddings (Voyage), classificação e chat (Anthropic). O modelo
vem do app_config (com fallback), então trocar o modelo no painel afeta as
próximas chamadas sem reiniciar (ADM-33/34). Nos testes, injeta-se um fake.
"""
from __future__ import annotations

from services.rag import CLASSIFIER_PROMPT, DEFAULT_DOC_TYPE, DOC_TYPES, TYPE_CLASSIFIER_PROMPT


class AIService:
    def __init__(self, anthropic_key, voyage_key, models_getter):
        self._akey = anthropic_key
        self._vkey = voyage_key
        # models_getter() -> {"claude_model","voyage_model"}
        self._models = models_getter

    def _voyage(self):
        import voyageai
        return voyageai.Client(api_key=self._vkey)

    def _anthropic(self):
        from anthropic import Anthropic
        return Anthropic(api_key=self._akey)

    def embed_documents(self, chunks: list[str]) -> list[list[float]]:
        model = self._models()["voyage_model"]
        vc = self._voyage()
        out = []
        for i in range(0, len(chunks), 64):
            r = vc.embed(chunks[i:i + 64], model=model, input_type="document")
            out.extend(r.embeddings)
        return out

    def embed_query(self, query: str) -> list[float]:
        model = self._models()["voyage_model"]
        return self._voyage().embed([query], model=model, input_type="query").embeddings[0]

    def is_relevant(self, alias: str, sample: str) -> bool:
        """Classificador. Fail-closed: erro propaga (o chamador bloqueia)."""
        model = self._models()["claude_model"]
        resp = self._anthropic().messages.create(
            model=model, max_tokens=10, system=CLASSIFIER_PROMPT,
            messages=[{"role": "user", "content": f"Nome: {alias}\n\nTrecho:\n{sample}"}],
        )
        return resp.content[0].text.strip().upper().startswith("YES")

    def classify_type(self, alias: str, sample: str) -> str:
        """Segunda camada: tipo do documento. Erro propaga (caller faz fallback)."""
        model = self._models()["claude_model"]
        resp = self._anthropic().messages.create(
            model=model, max_tokens=15, system=TYPE_CLASSIFIER_PROMPT,
            messages=[{"role": "user", "content": f"Nome: {alias}\n\nTrecho:\n{sample}"}],
        )
        answer = resp.content[0].text.strip().lower()
        for t in DOC_TYPES:
            if t in answer:
                return t
        return DEFAULT_DOC_TYPE

    def identify_squad(self, text: str):
        """Nome da squad descrita no trecho, ou None se não identificável."""
        model = self._models()["claude_model"]
        resp = self._anthropic().messages.create(
            model=model, max_tokens=20,
            system="Qual squad/time este trecho descreve? Responda APENAS o nome da squad, ou exatamente NONE se não houver uma squad claramente identificável.",
            messages=[{"role": "user", "content": text[:3000]}],
        )
        name = resp.content[0].text.strip()
        return None if name.upper().startswith("NONE") or not name else name

    def stream_chat(self, system: str, question: str):
        model = self._models()["claude_model"]
        with self._anthropic().messages.stream(
            model=model, max_tokens=4096, system=system,
            messages=[{"role": "user", "content": question}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    def embedding_model(self) -> str:
        return self._models()["voyage_model"]
