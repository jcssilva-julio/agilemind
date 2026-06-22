"""
Seção 8 — Segurança e regressão geral.

Fase 1 (implementada): SEC-04.
Demais (skip): SEC-01/02/03 (Fase 6), SEC-05 (E2E, Fase 7).

Casos: SEC-01 .. SEC-05 — ver tests/casos_de_teste.md (seção 8).
"""
import pytest


@pytest.mark.skip(reason="Fase 6: hardening (SQL injection)")
def test_sec_01_sql_injection(client): ...


@pytest.mark.skip(reason="Fase 6: hardening (XSS no alias)")
def test_sec_02_xss_no_alias(client): ...


@pytest.mark.skip(reason="Fase 6: hardening (CORS)")
def test_sec_03_cors(client): ...


def test_sec_04_master_nao_loga_como_usuario(client, master, make_user):
    """A senha master não vale como senha de login de um usuário."""
    make_user(email="sec4@x.com", password="senha123")
    r = client.post("/login", json={"email": "sec4@x.com", "password": master})
    assert r.status_code == 401


@pytest.mark.skip(reason="Fase 7: fluxo feliz E2E")
def test_sec_05_fluxo_feliz_completo(client): ...
