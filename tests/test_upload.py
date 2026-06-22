"""
Seção 4 — Upload e classificação de documentos (migrado + visibilidade).

Casos: UP-01 .. UP-13 — ver tests/casos_de_teste.md (seção 4).
Estado-alvo: PDFs no Supabase Storage, metadados em `documents`, campo visibility.
"""
import pytest

pytestmark = pytest.mark.skip(reason="TDD: upload migrado (Storage + visibility) ainda não implementado")


# 4.1 Upload básico (regressão do comportamento atual)
def test_up_01_pdf_agil_autenticado_private(client):
    """SSE extract->classify->chunk->embed->done; PDF no Storage; linha em documents."""
    raise NotImplementedError


def test_up_02_pdf_fora_de_escopo_rejeitado(client):
    """SSE rejected; nada no Storage; nenhuma linha em documents."""
    raise NotImplementedError


def test_up_03_arquivo_nao_pdf(client):
    """400 'Apenas PDFs são aceitos'; sem classificação/Storage."""
    raise NotImplementedError


def test_up_04_sem_arquivo(client):
    """400."""
    raise NotImplementedError


def test_up_05_pdf_sem_texto_extraivel(client):
    """SSE error 'PDF sem texto extraível'."""
    raise NotImplementedError


def test_up_06_excede_tamanho_maximo(client):
    """Rejeitado antes de processar (MAX_CONTENT_LENGTH = 50MB)."""
    raise NotImplementedError


def test_up_07_falha_classificacao_anthropic(client):
    """BLOQUEAR (fail-closed): SSE error/rejected; nada persiste no Storage/banco."""
    raise NotImplementedError


# 4.2 Visibilidade (funcionalidade nova)
def test_up_08_pergunta_visibilidade_exibida(client):
    """Frontend pergunta visibilidade antes de finalizar."""
    raise NotImplementedError


def test_up_09_marcado_como_privado(client):
    """visibility='private', owner = usuário logado."""
    raise NotImplementedError


def test_up_10_marcado_como_publico(client):
    """visibility='public'."""
    raise NotImplementedError


def test_up_11_sem_escolher_visibilidade(client):
    """Não prossegue sem o campo visibility."""
    raise NotImplementedError


def test_up_12_alterar_visibilidade_pelo_dono(client):
    """PATCH troca private<->public sem reindexar."""
    raise NotImplementedError


def test_up_13_outro_usuario_nao_altera_visibilidade(client):
    """403 quando B não é o owner."""
    raise NotImplementedError
