"""
Seção 8 — Segurança e regressão geral.

Casos: SEC-01 .. SEC-05 — ver tests/casos_de_teste.md (seção 8).
SEC-05 é o fluxo feliz ponta a ponta (replica as regras das seções 3 a 6).
"""
import pytest

pytestmark = pytest.mark.skip(reason="TDD: hardening de segurança ainda não implementado")


def test_sec_01_sql_injection(client):
    """alias/question com SQL malicioso não afeta o banco; queries parametrizadas."""
    raise NotImplementedError


def test_sec_02_xss_no_alias(client):
    """Frontend escapa alias <script> ao renderizar (confirmar escapeHtml)."""
    raise NotImplementedError


def test_sec_03_cors(client):
    """Domínio não autorizado bloqueado, se CORS for restringido."""
    raise NotImplementedError


def test_sec_04_master_nao_loga_como_usuario(client):
    """401; senha master só vale em /admin/create-user."""
    raise NotImplementedError


def test_sec_05_fluxo_feliz_completo(client):
    """E2E: criar via master -> login -> privado -> perguntar -> público ->
    2º user vê público mas não privado -> não exclui público -> exclui privado."""
    raise NotImplementedError
