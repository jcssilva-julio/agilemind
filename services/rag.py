"""Funções puras de RAG: extração de PDF, chunking e similaridade."""
from __future__ import annotations

import io
from typing import List

import numpy as np

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 8

CLASSIFIER_PROMPT = """Você é um classificador binário de documentos. Responda APENAS com YES ou NO, sem mais nada.

YES: o documento é relacionado a qualquer um destes temas:
- Times de tecnologia, squads, agilidade, Scrum, Kanban, SAFe
- Gestão de projetos de software, produto digital, DevOps
- Relatórios de squad, sprint, velocity, burndown, backlog
- TI em geral, infraestrutura, segurança, arquitetura de software
- OKRs, KPIs e métricas de times de tecnologia

NO: qualquer outro tipo de documento, incluindo:
- Contratos jurídicos, imobiliários, trabalhistas
- Documentos financeiros pessoais, notas fiscais, extratos
- Culinária, literatura, medicina, direito, engenharia civil
- Qualquer tema sem relação com TI ou agilidade"""

SYSTEM_PROMPT = """Você é o AgileMind, um agente especialista em metodologias ágeis e gestão de times de tecnologia.

Responda EXCLUSIVAMENTE com base no documento carregado, sobre agilidade (Scrum, Kanban, SAFe), métricas (velocity, burndown, lead/cycle time, DORA), cerimônias, backlog, OKRs, impedimentos, dívida técnica, coaching, relatórios de squad e TI em geral.

DOCUMENTO CARREGADO: {alias}

LIMITES:
- Se a informação não estiver no documento, diga claramente.
- Se a pergunta não tiver relação com agilidade ou TI, responda apenas: "Essa pergunta está fora do meu escopo. Sou especialista em agilidade e análise de reports de squads. Posso te ajudar com algo relacionado ao documento carregado?"

INSTRUÇÕES:
1. Para gráficos (burndown, velocity): gere HTML completo com Chart.js em bloco ```html e explique.
2. Para análises: seja construtivo e proponha ações concretas.
3. Use markdown rico (tabelas, listas, negrito em métricas).

CONTEÚDO DO DOCUMENTO:
{context}"""


def extract_pdf_text(data: bytes) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for pg in pdf.pages:
            t = pg.extract_text()
            if t:
                pages.append(t)
    return "\n\n".join(pages)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i:i + size])
        if chunk.strip():
            chunks.append(chunk)
        i += size - overlap
    return chunks


def cosine_sim(a, b) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def retrieve_top_k(query_emb, chunks: List[str], embeddings, k: int = TOP_K) -> List[str]:
    sims = [(cosine_sim(query_emb, emb), chunk) for chunk, emb in zip(chunks, embeddings)]
    sims.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in sims[:k]]
