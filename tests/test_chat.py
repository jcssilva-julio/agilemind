"""
Seção 5 — Chat / RAG com isolamento de visibilidade.

Casos: CHAT-01 .. CHAT-07 — ver tests/casos_de_teste.md (seção 5).
CHAT-07 é o teste crítico da remoção do app_state global (isolamento por usuário).
"""
import pytest

pytestmark = pytest.mark.skip(reason="TDD: chat isolado por usuário ainda não implementado")


def test_chat_01_doc_privado_proprio(client):
    """RAG normal, streaming token a token."""
    raise NotImplementedError


def test_chat_02_doc_privado_de_outro(client):
    """404 (tratado como inexistente para B); não carrega."""
    raise NotImplementedError


def test_chat_03_doc_publico_de_outro(client):
    """Permitido; RAG normal."""
    raise NotImplementedError


def test_chat_04_pergunta_fora_de_escopo(client):
    """Recusa padrão do SYSTEM_PROMPT."""
    raise NotImplementedError


def test_chat_05_sem_documento_carregado(client):
    """400 'Nenhum report indexado...'; isolado por usuário, não global."""
    raise NotImplementedError


def test_chat_06_pedido_de_grafico(client):
    """Resposta com bloco HTML + Chart.js."""
    raise NotImplementedError


def test_chat_07_dois_usuarios_simultaneos(client):
    """CRÍTICO: cada resposta usa só o doc certo; sem vazamento entre sessões."""
    raise NotImplementedError
