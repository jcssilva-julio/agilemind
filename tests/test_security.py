"""
Seção 8 — Segurança e regressão geral.

Implementados: SEC-01 (SQL injection), SEC-02 (XSS no alias), SEC-03 (CORS), SEC-04.
SEC-05 (E2E) fica para a Fase 7.
"""
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


@pytest.mark.skip(reason="Fase 7: fluxo feliz E2E em produção")
def test_sec_05_fluxo_feliz_completo(): ...
