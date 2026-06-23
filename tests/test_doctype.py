"""
Classificação de tipo de documento + chunking/retrieval multi-squad (TYPE-01..25).

Cobre o plumbing testável: fallback, ordem das etapas, squad_name nos chunks,
prompt dinâmico, retrieval ciente de squad e correção manual. Os casos de
ACURÁCIA do classificador e de QUALIDADE da resposta dependem do modelo real e
ficam como validação manual (skip documentado).
Ver tests/casos_de_teste_doctype.md.
"""
import io
import json

import pytest

from services import rag

PDF = b"%PDF fake"


def sse(resp):
    return [json.loads(l[6:]) for l in resp.get_data(as_text=True).splitlines()
            if l.startswith("data: ")]


@pytest.fixture
def user_client(client, make_user, login):
    u = make_user(email="dono@x.com", password="senha123")
    login(u["email"], "senha123")
    return client, u


def _upload(client, visibility="private", alias="Doc"):
    return client.post("/upload", data={
        "file": (io.BytesIO(PDF), "r.pdf"), "alias": alias, "visibility": visibility,
    }, content_type="multipart/form-data")


def _pages(monkeypatch, pages):
    monkeypatch.setattr("services.rag.extract_pdf_pages", lambda d: pages)


# ═══════════════ 6.1 Classificação de tipo ═══════════════
def test_type_06_fallback_quando_classificador_falha(user_client, container, monkeypatch):
    client, _ = user_client
    _pages(monkeypatch, ["sprint velocity burndown " * 30])
    container.ai.raise_on_classify_type = True       # classificador de tipo fora do ar
    done = [e for e in sse(_upload(client)) if e["type"] == "done"]
    assert done and done[0]["document_type"] == "other_it_document"   # fallback, upload não interrompe


def test_type_07_tipo_nao_roda_sem_aprovar_dominio(user_client, container, monkeypatch):
    client, _ = user_client
    _pages(monkeypatch, ["receita de bolo de fubá"])
    container.ai.relevant = False
    container.ai.classify_type_calls = 0
    ev = sse(_upload(client))
    assert any(e["type"] == "rejected" for e in ev)
    assert container.ai.classify_type_calls == 0     # classificador de tipo nunca chamado


# Acurácia da classificação → comportamento do modelo (validação manual)
@pytest.mark.skip(reason="Acurácia do classificador = comportamento do modelo; validar manual")
def test_type_01_05_08_acuracia(): ...


# ═══════════════ 6.2 Chunking com detecção de squad ═══════════════
def test_type_09_chunks_recebem_squad_name(user_client, container, monkeypatch):
    client, _ = user_client
    container.ai.doc_type = "squad_report_multi"
    container.ai.known_squads = ["Phoenix Pay", "Atlas"]
    _pages(monkeypatch, ["Squad Phoenix Pay velocity sprint 33 " * 15,
                         "Squad Atlas burndown sprint 33 " * 15])
    did = [e for e in sse(_upload(client)) if e["type"] == "done"][0]["document_id"]
    squads = {r["squad_name"] for r in container.chunks.get_by_document(did)}
    assert "Phoenix Pay" in squads and "Atlas" in squads


def test_type_10_11_conteudo_geral_fica_nulo(user_client, container, monkeypatch):
    client, _ = user_client
    container.ai.doc_type = "squad_report_multi"
    container.ai.known_squads = ["Phoenix Pay"]      # 1ª página não tem squad identificável
    _pages(monkeypatch, ["Sumario executivo geral do documento " * 15,
                         "Squad Phoenix Pay velocity " * 15])
    did = [e for e in sse(_upload(client)) if e["type"] == "done"][0]["document_id"]
    squads = [r["squad_name"] for r in container.chunks.get_by_document(did)]
    assert None in squads and "Phoenix Pay" in squads


def test_type_12_single_sem_squad_name(user_client, container, monkeypatch):
    client, _ = user_client
    container.ai.doc_type = "squad_report_single"
    _pages(monkeypatch, ["velocity burndown backlog " * 30])
    did = [e for e in sse(_upload(client)) if e["type"] == "done"][0]["document_id"]
    assert all(r["squad_name"] is None for r in container.chunks.get_by_document(did))


# ═══════════════ 6.3 Retrieval ciente de squad ═══════════════
def _seed_multi(container, owner_id):
    did = container.documents.create(owner_id, "Multi", "m.pdf", "p", "private", "squad_report_multi")
    container.chunks.create_many(did, [
        {"chunk_index": 0, "content": "PHOENIX_DATA velocity", "embedding": [1.0, 1.0], "squad_name": "Phoenix Pay"},
        {"chunk_index": 1, "content": "ATLAS_DATA velocity", "embedding": [1.0, 1.0], "squad_name": "Atlas"},
        {"chunk_index": 2, "content": "GERAL_DATA resumo", "embedding": [1.0, 1.0], "squad_name": None},
    ], "m")
    return did


def test_type_13_retrieval_prioriza_squad_mencionada(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = _seed_multi(container, a["user_id"])
    login(a["email"], "senha123")
    sse(client.post("/chat", json={"question": "qual a velocity da Phoenix Pay?", "document_id": did}))
    sysp = container.ai.last_system
    assert "PHOENIX_DATA" in sysp and "GERAL_DATA" in sysp and "ATLAS_DATA" not in sysp


def test_type_17_single_doc_nao_aciona_logica_squad(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = container.documents.create(a["user_id"], "Single", "s.pdf", "p", "private", "squad_report_single")
    container.chunks.create_many(did, [{"chunk_index": 0, "content": "velocity 30", "embedding": [1.0, 1.0], "squad_name": None}], "m")
    login(a["email"], "senha123")
    ev = sse(client.post("/chat", json={"question": "qual a velocity?", "document_id": did}))
    assert any(e["type"] == "token" for e in ev)
    assert rag.TYPE_INSTRUCTIONS["squad_report_single"][:25] in container.ai.last_system


@pytest.mark.skip(reason="Qualidade/separação da resposta = comportamento do modelo; validar manual")
def test_type_14_16_resposta_separa_squads(): ...


# ═══════════════ 6.4 Prompt dinâmico por tipo ═══════════════
@pytest.mark.parametrize("dtype", list(rag.DOC_TYPES))
def test_type_18_22_prompt_por_tipo(dtype):
    prompt = rag.build_system_prompt("MeuDoc", dtype, "CONTEUDO_X")
    assert rag.TYPE_INSTRUCTIONS[dtype][:40] in prompt        # bloco específico presente
    assert rag.DOC_TYPE_LABELS[dtype] in prompt               # rótulo do tipo
    assert "CONTEUDO_X" in prompt and "MeuDoc" in prompt


def test_prompt_tipo_invalido_usa_fallback():
    prompt = rag.build_system_prompt("D", "tipo_inexistente", "ctx")
    assert rag.TYPE_INSTRUCTIONS["other_it_document"][:40] in prompt


@pytest.mark.skip(reason="Resposta não calcular velocity de CV = comportamento do modelo; validar manual")
def test_type_20_23_resposta_por_tipo(): ...


# ═══════════════ Correção manual do tipo (decisão: permitir) ═══════════════
def test_type_corrigir_pelo_dono(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = container.documents.create(a["user_id"], "D", "d.pdf", "p", "private", "cv_resume")
    login(a["email"], "senha123")
    r = client.patch(f"/pdf/{did}/type", json={"document_type": "squad_report_single"})
    assert r.status_code == 200
    assert container.documents.get(did)["document_type"] == "squad_report_single"


def test_type_corrigir_tipo_invalido(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = container.documents.create(a["user_id"], "D", "d.pdf", "p", "private", "cv_resume")
    login(a["email"], "senha123")
    assert client.patch(f"/pdf/{did}/type", json={"document_type": "xpto"}).status_code == 400


def test_type_corrigir_outro_usuario_403(client, make_user, login, container):
    dono = make_user(email="dono@x.com", password="senha123")
    did = container.documents.create(dono["user_id"], "D", "d.pdf", "p", "private", "cv_resume")
    outro = make_user(email="outro@x.com", password="senha123")
    login(outro["email"], "senha123")
    assert client.patch(f"/pdf/{did}/type", json={"document_type": "cv_resume"}).status_code == 403


# ═══════════════ 6.5 Regressão (E2E) → manual ═══════════════
@pytest.mark.skip(reason="Fluxo E2E completo = validação manual no app")
def test_type_24_25_regressao_e2e(): ...
