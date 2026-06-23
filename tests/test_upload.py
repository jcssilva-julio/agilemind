"""
Seção 4.1 — Upload migrado para Storage + Postgres (UP-01..07).
4.2 (visibilidade UP-08..13) fica para a Fase 4. Ver casos_de_teste.md.
"""
import io
import json

import pytest

PDF = b"%PDF-1.4 fake bytes"


def sse(resp):
    return [json.loads(l[6:]) for l in resp.get_data(as_text=True).splitlines()
            if l.startswith("data: ")]


def _upload(client, filename="report.pdf", alias="Squad", visibility="private"):
    return client.post("/upload", data={
        "file": (io.BytesIO(PDF), filename), "alias": alias, "visibility": visibility,
    }, content_type="multipart/form-data")


@pytest.fixture
def user_client(client, make_user, login):
    u = make_user(email="dono@x.com", password="senha123")
    login(u["email"], "senha123")
    return client, u


def _mock_text(monkeypatch, text):
    monkeypatch.setattr("services.rag.extract_pdf_text", lambda d: text)


def test_up_01_pdf_agil_autenticado(user_client, container, monkeypatch):
    client, u = user_client
    _mock_text(monkeypatch, "sprint velocity burndown backlog scrum " * 50)
    ev = sse(_upload(client))
    steps = [e for e in ev if e["type"] == "progress"]
    done = [e for e in ev if e["type"] == "done"]
    assert {"extract", "classify", "chunk", "embed", "store"} <= {e["step"] for e in steps}
    assert done, ev
    doc = container.documents.get(done[0]["document_id"])
    assert doc["owner_user_id"] == u["user_id"] and doc["visibility"] == "private"
    assert container.chunks.get_by_document(doc["id"])           # chunks no Postgres
    assert len(container.storage.files) == 1                     # PDF no Storage


def test_up_02_pdf_fora_de_escopo_rejeitado(user_client, container, monkeypatch):
    client, _ = user_client
    container.ai.relevant = False
    _mock_text(monkeypatch, "receita de bolo de fubá com goiabada")
    ev = sse(_upload(client))
    assert any(e["type"] == "rejected" for e in ev)
    assert not container.documents.docs and not container.storage.files


def test_up_03_arquivo_nao_pdf(user_client):
    client, _ = user_client
    r = _upload(client, filename="nota.txt")
    assert r.status_code == 400


def test_up_04_sem_arquivo(user_client):
    client, _ = user_client
    r = client.post("/upload", data={"alias": "x"}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_up_05_pdf_sem_texto(user_client, monkeypatch):
    client, _ = user_client
    _mock_text(monkeypatch, "   ")
    ev = sse(_upload(client))
    assert any(e["type"] == "error" and "extraível" in e["message"] for e in ev)


def test_up_06_excede_tamanho(user_client, app):
    client, _ = user_client
    app.config["MAX_CONTENT_LENGTH"] = 10  # força o limite
    r = client.post("/upload", data={"file": (io.BytesIO(b"x" * 5000), "big.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 413


def test_up_07_falha_classificacao_fail_closed(user_client, container, monkeypatch):
    client, _ = user_client
    container.ai.raise_on_classify = True   # Anthropic fora do ar
    _mock_text(monkeypatch, "sprint velocity burndown " * 30)
    ev = sse(_upload(client))
    assert any(e["type"] == "rejected" for e in ev)              # bloqueia
    assert not container.documents.docs and not container.storage.files


# 4.2 Visibilidade — Fase 4
@pytest.mark.skip(reason="Fase 4: visibilidade (UX de escolha no upload)")
def test_up_08_pergunta_visibilidade(): ...
@pytest.mark.skip(reason="Fase 4")
def test_up_09_marcado_privado(): ...
@pytest.mark.skip(reason="Fase 4")
def test_up_10_marcado_publico(): ...
@pytest.mark.skip(reason="Fase 4")
def test_up_11_sem_escolher(): ...
@pytest.mark.skip(reason="Fase 4")
def test_up_12_alterar_visibilidade(): ...
@pytest.mark.skip(reason="Fase 4")
def test_up_13_outro_nao_altera(): ...
