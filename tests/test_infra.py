"""
Seção 7 — Infraestrutura e deploy (Railway + Supabase).

A maioria é verificação no ambiente de produção (Railway) e está documentada em
docs/DEPLOY_RAILWAY.md como checklist manual. INF-02 é testável localmente.
"""
import pytest


def test_inf_02_app_responde_com_login(client):
    """A raiz não renderiza o chat sem sessão — leva ao login (confirma AUTH-21)."""
    r = client.get("/")
    assert r.status_code in (301, 302) and "/login" in r.headers["Location"]


@pytest.mark.skip(reason="Produção: conferir variáveis no painel do Railway")
def test_inf_01_env_vars(): ...
@pytest.mark.skip(reason="Produção: sem erros de conexão Postgres no boot do Railway")
def test_inf_03_conexao_postgres(): ...
@pytest.mark.skip(reason="Produção: upload de teste aparece no bucket (validado local na Fase 3)")
def test_inf_04_storage_funcional(): ...
@pytest.mark.skip(reason="Produção: monitorar consumo do plano gratuito no painel")
def test_inf_05_limite_plano(): ...
@pytest.mark.skip(reason="Produção: bucket privado — URL direta sem auth deve negar")
def test_inf_06_bucket_privado(): ...
@pytest.mark.skip(reason="Produção: Railway força HTTPS (ProxyFix no wsgi.py)")
def test_inf_07_https_obrigatorio(): ...
