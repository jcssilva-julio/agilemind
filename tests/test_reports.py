"""
Seção 6 — Gestão de relatórios indexados (visibilidade + permissões).

Casos: MNG-01 .. MNG-08 — ver tests/casos_de_teste.md (seção 6).
"""
import pytest

pytestmark = pytest.mark.skip(reason="TDD: gestão de relatórios multiusuário ainda não implementada")


def test_mng_01_listar_privados_proprios_mais_publicos(client):
    """Privados de A + todos públicos. FALHA se um privado de outro dono aparecer."""
    raise NotImplementedError


def test_mng_02_listar_sem_documentos(client):
    """Lista vazia."""
    raise NotImplementedError


def test_mng_03_carregar_doc_proprio(client):
    """200; ativa na sessão."""
    raise NotImplementedError


def test_mng_04_carregar_publico_de_outro(client):
    """200; ativa."""
    raise NotImplementedError


def test_mng_05_carregar_privado_de_outro(client):
    """404 (inexistente para B); não ativa."""
    raise NotImplementedError


def test_mng_06_excluir_doc_proprio(client):
    """Confirma antes; remove de Storage, documents, document_chunks e da lista."""
    raise NotImplementedError


def test_mng_07_excluir_doc_de_outro(client):
    """403; nada removido."""
    raise NotImplementedError


def test_mng_08_excluir_publico_sem_ser_dono(client):
    """403; público dá leitura, não exclusão."""
    raise NotImplementedError
