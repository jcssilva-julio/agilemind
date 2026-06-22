"""
Seção 3 — Autenticação e senha master.

Fase 1 (implementada): AUTH-01..06, 08, 09, 10..15, 25, 26.
Fases posteriores (skip): AUTH-07 (HTTPS, Fase 7), AUTH-16..24 (proteção de
rotas/sessão, Fase 2).

Casos: ver tests/casos_de_teste.md (seção 3).
"""
import pytest


# ─────────────────────────────────────────────────────────────────────
# 3.1 Criação de usuário via senha master
# ─────────────────────────────────────────────────────────────────────
def test_auth_01_criar_usuario_com_master_correta(client, master):
    r = client.post("/admin/create-user", json={
        "master_password": master, "email": "novo@x.com", "password": "senha123", "nome": "Novo"
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body["ok"] and body.get("user_id")
    # Senha master não vaza na resposta (AUTH-01).
    assert master not in r.get_data(as_text=True)


def test_auth_02_master_incorreta(client, master):
    r = client.post("/admin/create-user", json={
        "master_password": "errada", "email": "a@x.com", "password": "senha123", "nome": "A"
    })
    assert r.status_code == 401
    # Login depois deve falhar (não foi criado).
    assert client.post("/login", json={"email": "a@x.com", "password": "senha123"}).status_code == 401


def test_auth_03_sem_master(client):
    r = client.post("/admin/create-user", json={
        "email": "a@x.com", "password": "senha123", "nome": "A"
    })
    assert r.status_code == 400


def test_auth_04_email_ja_existente(client, master, make_user):
    make_user(email="dup@x.com")
    r = client.post("/admin/create-user", json={
        "master_password": master, "email": "dup@x.com", "password": "outra123", "nome": "Dup"
    })
    assert r.status_code == 409


def test_auth_05_email_invalido(client, master):
    r = client.post("/admin/create-user", json={
        "master_password": master, "email": "abc@", "password": "senha123", "nome": "A"
    })
    assert r.status_code == 400


def test_auth_06_senha_fraca(client, master):
    r = client.post("/admin/create-user", json={
        "master_password": master, "email": "a@x.com", "password": "123", "nome": "A"
    })
    assert r.status_code == 400


@pytest.mark.skip(reason="Fase 7: HTTPS forçado é responsabilidade do Railway")
def test_auth_07_exige_https_em_producao():
    ...


def test_auth_08_master_nunca_em_logs(client, master, caplog):
    import logging
    with caplog.at_level(logging.DEBUG):
        client.post("/admin/create-user", json={
            "master_password": master, "email": "log@x.com", "password": "senha123", "nome": "L"
        })
        client.post("/admin/create-user", json={
            "master_password": "errada", "email": "log2@x.com", "password": "senha123", "nome": "L"
        })
    assert master not in caplog.text


def test_auth_09_master_vem_de_env(monkeypatch):
    from config import Config
    monkeypatch.setenv("MASTER_PASSWORD", "do-ambiente")
    assert Config().MASTER_PASSWORD == "do-ambiente"


# ─────────────────────────────────────────────────────────────────────
# 3.2 Login
# ─────────────────────────────────────────────────────────────────────
def test_auth_10_login_credenciais_validas(client, make_user):
    u = make_user(email="login@x.com", password="senha123")
    r = client.post("/login", json={"email": u["email"], "password": "senha123"})
    assert r.status_code == 200
    # Cookie de sessão foi setado.
    assert any("agilemind_session" in h for h in r.headers.getlist("Set-Cookie"))


def test_auth_11_login_senha_incorreta(client, make_user):
    make_user(email="x@x.com", password="senha123")
    r = client.post("/login", json={"email": "x@x.com", "password": "errada"})
    assert r.status_code == 401
    msg = r.get_json()["error"]
    assert "inválid" in msg.lower()


def test_auth_12_login_email_inexistente(client, make_user):
    make_user(email="existe@x.com", password="senha123")
    r1 = client.post("/login", json={"email": "naoexiste@x.com", "password": "qualquer"})
    r2 = client.post("/login", json={"email": "existe@x.com", "password": "errada"})
    # Mesma mensagem genérica para inexistente e senha errada (não revela existência).
    assert r1.status_code == r2.status_code == 401
    assert r1.get_json()["error"] == r2.get_json()["error"]


def test_auth_13_login_campos_vazios(client):
    r = client.post("/login", json={"email": "", "password": ""})
    assert r.status_code == 400


def test_auth_14_sem_self_signup_publico(client):
    # Não deve existir rota de cadastro público.
    assert client.post("/register", json={}).status_code == 404
    assert client.post("/signup", json={}).status_code == 404


def test_auth_15_rate_limiting_login(client, make_user):
    make_user(email="rl@x.com", password="senha123")
    for _ in range(5):
        assert client.post("/login", json={"email": "rl@x.com", "password": "errada"}).status_code == 401
    # 6ª tentativa: bloqueado.
    assert client.post("/login", json={"email": "rl@x.com", "password": "errada"}).status_code == 429


# ─────────────────────────────────────────────────────────────────────
# 3.3 Sessão e proteção de rotas — Fase 2
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_16_upload_sem_auth(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_17_chat_sem_auth(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_18_pdf_indices_sem_auth(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_19_pdf_load_sem_auth(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_20_pdf_delete_sem_auth(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_21_index_sem_sessao_redireciona_login(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_22_sessao_expirada_rejeitada(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_23_logout_encerra_sessao(client): ...
@pytest.mark.skip(reason="Fase 2: proteção de rotas")
def test_auth_24_token_de_outro_usuario(client): ...


# ─────────────────────────────────────────────────────────────────────
# 3.4 Gestão de usuários pós-criação (só via senha master)
# ─────────────────────────────────────────────────────────────────────
def test_auth_25_desativar_usuario_via_master(client, master, make_user):
    make_user(email="off@x.com", password="senha123")
    r = client.post("/admin/deactivate-user", json={"master_password": master, "email": "off@x.com"})
    assert r.status_code == 200
    assert master not in r.get_data(as_text=True)


def test_auth_26_usuario_desativado_nao_loga(client, master, make_user):
    make_user(email="off2@x.com", password="senha123")
    client.post("/admin/deactivate-user", json={"master_password": master, "email": "off2@x.com"})
    r = client.post("/login", json={"email": "off2@x.com", "password": "senha123"})
    assert r.status_code == 401
