"""
Seção 5 — Chat / RAG com isolamento por usuário (CHAT-01..07).
CHAT-07 é o teste crítico: sem estado global, sem vazamento entre usuários.
"""
import json

import pytest


def sse(resp):
    return [json.loads(l[6:]) for l in resp.get_data(as_text=True).splitlines()
            if l.startswith("data: ")]


def _doc_with_chunk(container, owner_id, alias, visibility, content):
    did = container.documents.create(owner_id, alias, f"{alias}.pdf", "p", visibility)
    container.chunks.create_many(did, [{"chunk_index": 0, "content": content, "embedding": [1.0, 1.0]}], "m")
    return did


def test_chat_01_doc_privado_proprio(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = _doc_with_chunk(container, a["user_id"], "Meu", "private", "velocity da sprint 12")
    login(a["email"], "senha123")
    ev = sse(client.post("/chat", json={"question": "qual a velocity?", "document_id": did}))
    assert any(e["type"] == "token" for e in ev) and any(e["type"] == "done" for e in ev)


def test_chat_02_doc_privado_de_outro(client, make_user, login, container):
    b = make_user(email="b@x.com", password="senha123")
    did = _doc_with_chunk(container, b["user_id"], "DeB", "private", "segredo")
    a = make_user(email="a@x.com", password="senha123")
    login(a["email"], "senha123")
    assert client.post("/chat", json={"question": "oi", "document_id": did}).status_code == 404


def test_chat_03_doc_publico_de_outro(client, make_user, login, container):
    b = make_user(email="b@x.com", password="senha123")
    did = _doc_with_chunk(container, b["user_id"], "PubB", "public", "burndown público")
    a = make_user(email="a@x.com", password="senha123")
    login(a["email"], "senha123")
    ev = sse(client.post("/chat", json={"question": "resuma", "document_id": did}))
    assert any(e["type"] == "token" for e in ev)


@pytest.mark.skip(reason="Recusa fora de escopo é comportamento do modelo (SYSTEM_PROMPT); validar manualmente")
def test_chat_04_fora_de_escopo(): ...


def test_chat_05_sem_documento(client, make_user, login):
    u = make_user(email="a@x.com", password="senha123")
    login(u["email"], "senha123")
    r = client.post("/chat", json={"question": "oi"})  # sem document_id
    assert r.status_code == 400


def test_chat_06_pedido_de_grafico(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = _doc_with_chunk(container, a["user_id"], "Meu", "private", "dados de burndown")
    login(a["email"], "senha123")
    ev = sse(client.post("/chat", json={"question": "gere um burndown", "document_id": did}))
    assert any(e["type"] == "token" for e in ev)


def test_chat_07_dois_usuarios_sem_vazamento(client, app, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    b = make_user(email="b@x.com", password="senha123")
    doc_a = _doc_with_chunk(container, a["user_id"], "DocA", "private", "ALPHA_CONTENT")
    doc_b = _doc_with_chunk(container, b["user_id"], "DocB", "private", "BETA_CONTENT")

    ca = app.test_client(); ca.post("/login", json={"email": a["email"], "password": "senha123"})
    cb = app.test_client(); cb.post("/login", json={"email": b["email"], "password": "senha123"})

    sse(ca.post("/chat", json={"question": "q", "document_id": doc_a}))
    assert "ALPHA_CONTENT" in container.ai.last_system and "BETA_CONTENT" not in container.ai.last_system

    sse(cb.post("/chat", json={"question": "q", "document_id": doc_b}))
    assert "BETA_CONTENT" in container.ai.last_system and "ALPHA_CONTENT" not in container.ai.last_system

    # A não acessa o doc privado de B nem informando o id diretamente.
    assert ca.post("/chat", json={"question": "q", "document_id": doc_b}).status_code == 404
