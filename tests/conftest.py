"""
Configuração compartilhada do pytest para o AgileMind.

Aqui ficam as fixtures reutilizáveis pelos testes — principalmente o
`client`, que permite chamar as rotas do Flask sem subir o servidor.
"""
import sys
from pathlib import Path

import pytest

# Garante que o app.py (na raiz) seja importável a partir de tests/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def client():
    """Test client do Flask, com a app em modo de teste."""
    from app import app

    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


@pytest.fixture
def fixtures_dir():
    """Caminho para os arquivos de apoio (PDFs de exemplo, etc.)."""
    return Path(__file__).parent / "fixtures"
