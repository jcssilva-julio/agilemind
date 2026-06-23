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

# Tipos de documento (segunda camada de classificação) e fallback seguro.
DOC_TYPES = (
    "squad_report_single", "squad_report_multi",
    "cv_resume", "commercial_proposal", "other_it_document",
)
DEFAULT_DOC_TYPE = "other_it_document"

DOC_TYPE_LABELS = {
    "squad_report_single": "Report de squad (única)",
    "squad_report_multi": "Report de múltiplas squads",
    "cv_resume": "Currículo (CV) de profissional de TI",
    "commercial_proposal": "Proposta comercial de TI",
    "other_it_document": "Documento de TI (outro)",
}

# Classificador de TIPO (roda depois do classificador de domínio). TYPE-08:
# prioriza o propósito geral do documento sobre menções pontuais a agilidade.
TYPE_CLASSIFIER_PROMPT = """Classifique o documento em UMA categoria. Responda APENAS com o identificador, sem mais nada:

- squad_report_single: report de UMA squad/time (velocity, burndown, backlog de um time).
- squad_report_multi: report com MÚLTIPLAS squads, cada uma com seu cabeçalho/seção.
- cv_resume: currículo de um profissional (experiência, formação, habilidades).
- commercial_proposal: proposta comercial de TI (escopo, valores, prazos, fornecedor).
- other_it_document: qualquer outro documento de TI (política, arquitetura, etc.).

Regra de desempate: priorize o PROPÓSITO GERAL do documento. Um currículo que cita Scrum/sprints continua sendo cv_resume."""

SYSTEM_PROMPT_BASE = """Você é o AgileMind, um agente especialista em metodologias ágeis, gestão de times de tecnologia e documentos do universo de TI.

Responda EXCLUSIVAMENTE com base no documento carregado.

DOCUMENTO CARREGADO: {alias}
TIPO DE DOCUMENTO DETECTADO: {document_type_label}

{type_specific_instructions}

LIMITES:
- Se a informação não estiver no documento, diga claramente.
- Se a pergunta não tiver relação com o conteúdo do documento carregado, responda apenas: "Essa pergunta está fora do meu escopo para este documento. Posso te ajudar com algo relacionado ao conteúdo carregado?"

INSTRUÇÕES GERAIS:
- Use markdown rico (tabelas, listas, negrito em métricas-chave).
- Cite de onde no documento veio a informação quando relevante.

CONTEÚDO DO DOCUMENTO:
{context}"""

TYPE_INSTRUCTIONS = {
    "squad_report_single": """Este documento é um report de uma única squad/time.
- Trate todos os dados (velocity, burndown, backlog, impedimentos) como pertencentes a essa squad.
- Para gráficos (burndown, velocity): gere HTML completo com Chart.js em bloco ```html e explique como usar.
- Para análises de retrospectiva e saúde do time, seja construtivo e proponha ações concretas.""",
    "squad_report_multi": """Este documento contém dados de MÚLTIPLAS squads, identificadas por nome no cabeçalho de cada seção/página.
- Antes de responder, identifique explicitamente a qual squad cada trecho do contexto pertence.
- Nunca misture números de squads diferentes como se fossem de uma squad só.
- Se a pergunta não especificar a squad e houver mais de uma no contexto, liste os dados separados por squad, ou pergunte qual squad o usuário quer.
- Para gráficos: gere um gráfico por squad, ou um comparativo com legenda clara identificando cada squad.""",
    "cv_resume": """Este documento é um currículo (CV) de um profissional de TI.
- Responda sobre experiência, formação, habilidades técnicas, certificações e histórico de carreira.
- Não trate o conteúdo como dados de squad: não há velocity, burndown ou backlog aqui.
- Se pedirem opinião sobre adequação a uma vaga, baseie-se apenas no que está escrito, deixando claro que é leitura textual.""",
    "commercial_proposal": """Este documento é uma proposta comercial relacionada a TI.
- Responda sobre escopo, valores, prazos, condições e termos descritos na proposta.
- Não trate o conteúdo como dados de squad.
- Para comparações de custo-benefício, seja objetivo e baseie-se apenas no documento.""",
    "other_it_document": """Este é um documento de TI que não se encaixa em report de squad, CV ou proposta comercial.
- Responda com base no conteúdo apresentado, mantendo-se no domínio de TI e tecnologia.""",
}


def build_system_prompt(alias: str, document_type: str, context: str) -> str:
    """Monta o prompt de sistema com o bloco específico do tipo (UC-04)."""
    dt = document_type if document_type in TYPE_INSTRUCTIONS else DEFAULT_DOC_TYPE
    return SYSTEM_PROMPT_BASE.format(
        alias=alias,
        document_type_label=DOC_TYPE_LABELS.get(dt, "Documento de TI"),
        type_specific_instructions=TYPE_INSTRUCTIONS[dt],
        context=context,
    )


def extract_pdf_pages(data: bytes) -> List[str]:
    """Texto por página (preserva a estrutura para detecção de squad por seção)."""
    import pdfplumber
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for pg in pdf.pages:
            t = pg.extract_text()
            pages.append(t or "")
    return pages


def extract_pdf_text(data: bytes) -> str:
    return "\n\n".join(p for p in extract_pdf_pages(data) if p.strip())


def chunk_pages_with_squads(pages: List[str], squad_namer) -> List[dict]:
    """
    Chunking multi-squad: para cada página, identifica a squad (via squad_namer,
    que faz chamada ao modelo) e anexa squad_name a cada chunk daquela página.
    Páginas sem squad identificável ficam com squad_name=None (conteúdo geral).
    Retorna [{'content', 'squad_name'}].
    """
    out = []
    for page in pages:
        if not page.strip():
            continue
        squad = squad_namer(page)  # None se não identificável (não adivinha)
        for ch in chunk_text(page):
            out.append({"content": ch, "squad_name": squad})
    return out


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
