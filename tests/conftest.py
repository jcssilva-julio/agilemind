"""
Configuração compartilhada do pytest para o AgileMind.

Monta a app via create_app() injetando um Container com adaptadores FAKE
(em memória, sem rede). Assim os testes de auth/visibilidade rodam rápido e
determinísticos. Testes de integração reais (INF-*) usarão outra fixture.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Senha master usada em todos os testes desta suíte.
MASTER = "master-test-secret"


@pytest.fixture
def container():
    from config import Config
    from container import _assemble
    from tests.fakes import FakeAuthProvider, FakeProfilesRepo, FakeSessionsRepo

    cfg = Config(
        MASTER_PASSWORD=MASTER,
        FLASK_SECRET_KEY="test-secret",
        SUPABASE_URL="http://fake",
        SUPABASE_KEY="fake",
    )
    return _assemble(cfg, FakeAuthProvider(), FakeProfilesRepo(), FakeSessionsRepo())


@pytest.fixture
def app(container):
    from app import create_app

    application = create_app(config=container.config, container=container)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def master():
    return MASTER


@pytest.fixture
def make_user(client):
    """Cria um usuário via senha master e devolve suas credenciais."""
    def _make(email="user@agilemind.test", password="senha123", nome="User"):
        r = client.post(
            "/admin/create-user",
            json={"master_password": MASTER, "email": email, "password": password, "nome": nome},
        )
        assert r.status_code == 201, r.get_json()
        return {"email": email, "password": password, "user_id": r.get_json()["user_id"]}

    return _make


@pytest.fixture
def login(client):
    """Faz login e devolve o test client com o cookie de sessão setado."""
    def _login(email, password):
        r = client.post("/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.get_json()
        return client

    return _login


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"
