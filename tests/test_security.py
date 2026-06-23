"""
Seção 8 — Segurança e regressão geral.

Implementados: SEC-01 (SQL injection), SEC-02 (XSS no alias), SEC-03 (CORS), SEC-04.
SEC-05: fluxo feliz E2E (regras das seções 3 a 6 em sequência).
"""
import json

import pytest


def test_sec_01_sql_injection(client, make_user, login, container):
    """Entradas com sintaxe SQL são tratadas como dado (queries parametrizadas)."""
    u = make_user(email="a@x.com", password="senha123")
    login(u["email"], "senha123")
    # alias malicioso é armazenado literalmente, sem efeito colateral.
    payload = "Squad'; DROP TABLE documents;--"
    did = container.documents.create(u["user_id"], payload, "f.pdf", "p", "private")
    idx = client.get("/pdf/indices").get_json()["indices"]
    assert any(d["alias"] == payload for d in idx)        # guardado como texto
    # document_id forjado com injeção não casa nada → 404, sem erro 500.
    r = client.post("/chat", json={"question": "oi", "document_id": "x' OR '1'='1"})
    assert r.status_code == 404


def test_sec_02_xss_no_alias(client, make_user, login, container):
    """A API entrega o alias como dado JSON (não HTML); o frontend escapa ao render."""
    u = make_user(email="a@x.com", password="senha123")
    login(u["email"], "senha123")
    xss = "<script>alert('x')</script>"
    container.documents.create(u["user_id"], xss, "f.pdf", "p", "private")
    r = client.get("/pdf/indices")
    # Content-type JSON: o navegador não executa o conteúdo como HTML.
    assert r.content_type.startswith("application/json")
    # Dado preservado (o escaping acontece no render — escapeHtml no index.html).
    assert any(d["alias"] == xss for d in r.get_json()["indices"])


def test_sec_03_cors_sem_origin_aberto(client, make_user, login):
    """Não expomos CORS aberto (frontend e backend no mesmo domínio)."""
    u = make_user(email="a@x.com", password="senha123")
    login(u["email"], "senha123")
    r = client.get("/pdf/indices")
    assert "Access-Control-Allow-Origin" not in r.headers


def test_sec_04_master_nao_loga_como_usuario(client, master, make_user):
    """A senha master não vale como senha de login de um usuário."""
    make_user(email="sec4@x.com", password="senha123")
    r = client.post("/login", json={"email": "sec4@x.com", "password": master})
    assert r.status_code == 401


def _upload(c, alias, visibility):
    import io
    r = c.post("/upload", data={"file": (io.BytesIO(b"%PDF"), "r.pdf"),
               "alias": alias, "visibility": visibility},
               content_type="multipart/form-data")
    for line in r.get_data(as_text=True).splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev.get("type") == "done":
                return ev["document_id"]
    return None


def test_sec_05_fluxo_feliz_completo(app, master, monkeypatch):
    """Regressão E2E das regras das seções 3 a 6 em sequência."""
    monkeypatch.setattr("services.rag.extract_pdf_text", lambda d: "sprint velocity burndown " * 40)
    ca = app.test_client()

    # 1) Admin via master (bootstrap) + login
    assert ca.post("/admin/bootstrap", json={
        "master_password": master, "email": "a@x.com", "password": "senha123", "nome": "A"}).status_code == 201
    ca.post("/login", json={"email": "a@x.com", "password": "senha123"})
    # 2) Admin cria o segundo usuário
    assert ca.post("/admin/users", json={
        "email": "b@x.com", "nome": "B", "password": "senha123", "role": "user"}).status_code == 201

    # 3) A sobe documento privado e pergunta
    priv = _upload(ca, "Privado", "private")
    assert priv
    ev = [json.loads(l[6:]) for l in ca.post("/chat", json={"question": "qual a velocity?", "document_id": priv}).get_data(as_text=True).splitlines() if l.startswith("data: ")]
    assert any(e["type"] == "token" for e in ev)
    # 4) A sobe documento público
    pub = _upload(ca, "Publico", "public")

    # 5) Login como segundo usuário
    cb = app.test_client()
    cb.post("/login", json={"email": "b@x.com", "password": "senha123"})
    idx = cb.get("/pdf/indices").get_json()["indices"]
    aliases = [d["alias"] for d in idx]
    # 6) Vê o público, não vê o privado
    assert "Publico" in aliases and "Privado" not in aliases
    # 7) Tenta excluir o público (deve falhar)
    pub_id = next(d["document_id"] for d in idx if d["alias"] == "Publico")
    assert cb.post("/pdf/delete", json={"document_id": pub_id}).status_code == 403
    # 8) A exclui o próprio privado (deve funcionar)
    assert ca.post("/pdf/delete", json={"document_id": priv}).status_code == 200
