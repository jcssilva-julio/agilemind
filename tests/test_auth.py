"""
Seção 3 — Autenticação e sessão.

NOTA v2: a gestão de usuários via senha master direta (AUTH-01..06, 08, 25, 26)
foi SUBSTITUÍDA pela camada de administração (bootstrap + admin autenticado) —
ver tests/test_admin.py (ADM-*). Esses casos ficam aqui como skip de referência.

Mantidos: AUTH-09 (master de env), AUTH-10..24 (login/sessão/proteção).
"""
import pytest

_SUPERSEDED = "Substituído pela camada de administração v2 (ver test_admin.py / ADM-*)"


# 3.1 Criação via senha master — SUBSTITUÍDA pela v2
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_01_criar_usuario_com_master_correta(): ...
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_02_master_incorreta(): ...
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_03_sem_master(): ...
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_04_email_ja_existente(): ...
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_05_email_invalido(): ...
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_06_senha_fraca(): ...
@pytest.mark.skip(reason="Fase 7: HTTPS forçado é responsabilidade do Railway")
def test_auth_07_exige_https_em_producao(): ...
@pytest.mark.skip(reason=_SUPERSEDED)
def test_auth_08_master_nunca_em_logs(): ...


def test_auth_09_master_vem_de_env(monkeypatch):
    from config import Config
    monkeypatch.setenv("MASTER_PASSWORD", "do-ambiente")
    assert Config().MASTER_PASSWORD == "do-ambiente"


# 3.2 Login
def test_auth_10_login_credenciais_validas(client, make_user):
    u = make_user(email="login@x.com", password="senha123")
    r = client.post("/login", json={"email": u["email"], "password": "senha123"})
    assert r.status_code == 200
    assert any("agilemind_session" in h for h in r.headers.getlist("Set-Cookie"))


def test_auth_11_login_senha_incorreta(client, make_user):
    make_user(email="x@x.com", password="senha123")
    r = client.post("/login", json={"email": "x@x.com", "password": "errada"})
    assert r.status_code == 401
    assert "inválid" in r.get_json()["error"].lower()


def test_auth_12_login_email_inexistente(client, make_user):
    make_user(email="existe@x.com", password="senha123")
    r1 = client.post("/login", json={"email": "naoexiste@x.com", "password": "qualquer"})
    r2 = client.post("/login", json={"email": "existe@x.com", "password": "errada"})
    assert r1.status_code == r2.status_code == 401
    assert r1.get_json()["error"] == r2.get_json()["error"]


def test_auth_13_login_campos_vazios(client):
    assert client.post("/login", json={"email": "", "password": ""}).status_code == 400


def test_auth_14_sem_self_signup_publico(client):
    assert client.post("/register", json={}).status_code == 404
    assert client.post("/signup", json={}).status_code == 404


def test_auth_15_rate_limiting_login(client, make_user):
    make_user(email="rl@x.com", password="senha123")
    for _ in range(5):
        assert client.post("/login", json={"email": "rl@x.com", "password": "errada"}).status_code == 401
    assert client.post("/login", json={"email": "rl@x.com", "password": "errada"}).status_code == 429


# 3.3 Sessão e proteção de rotas
def _session_token(resp):
    for c in resp.headers.getlist("Set-Cookie"):
        if c.startswith("agilemind_session="):
            return c.split("=", 1)[1].split(";", 1)[0]
    return None


def test_auth_16_upload_sem_auth(client):
    assert client.post("/upload").status_code == 401


def test_auth_17_chat_sem_auth(client):
    assert client.post("/chat", json={"question": "oi"}).status_code == 401


def test_auth_18_pdf_indices_sem_auth(client):
    assert client.get("/pdf/indices").status_code == 401


def test_auth_19_pdf_load_sem_auth(client):
    assert client.post("/pdf/load", json={"filename": "x"}).status_code == 401


def test_auth_20_pdf_delete_sem_auth(client):
    assert client.post("/pdf/delete", json={"filename": "x"}).status_code == 401


def test_auth_21_index_sem_sessao_redireciona_login(client):
    r = client.get("/")
    assert r.status_code in (301, 302)
    assert "/login" in r.headers["Location"]


def test_auth_22_sessao_expirada_rejeitada(client, make_user, container):
    from datetime import datetime, timedelta, timezone
    u = make_user(email="exp@x.com", password="senha123")
    client.post("/login", json={"email": u["email"], "password": "senha123"})
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    for tok in list(container.sessions._s):
        container.sessions._s[tok]["expires_at"] = past
    assert client.get("/me").status_code == 401


def test_auth_23_logout_encerra_sessao(client, make_user):
    u = make_user(email="lo@x.com", password="senha123")
    r = client.post("/login", json={"email": u["email"], "password": "senha123"})
    token = _session_token(r)
    assert client.get("/me").status_code == 200
    client.post("/logout")
    r2 = client.get("/me", headers={"Cookie": f"agilemind_session={token}"})
    assert r2.status_code == 401


def test_auth_24_token_de_outro_usuario(client, make_user):
    a = make_user(email="a@x.com", password="senha123")
    client.post("/login", json={"email": a["email"], "password": "senha123"})
    r = client.get("/me", json={"user_id": "forjado-outro-usuario"})
    assert r.status_code == 200
    assert r.get_json()["user_id"] == a["user_id"]
