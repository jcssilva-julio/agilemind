"""
Configuração compartilhada do pytest para o AgileMind.

Monta a app via create_app() injetando um Container com adaptadores FAKE
(em memória, sem rede). Testes de integração reais usarão outra fixture.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MASTER = "master-test-secret"


@pytest.fixture
def container():
    from config import Config
    from container import _assemble
    from tests.fakes import (
        FakeAppConfigRepo, FakeAuditRepo, FakeAuthProvider, FakeDocumentsRepo,
        FakeModelValidator, FakeProfilesRepo, FakeSessionsRepo,
    )

    cfg = Config(
        MASTER_PASSWORD=MASTER, FLASK_SECRET_KEY="test-secret",
        SUPABASE_URL="http://fake", SUPABASE_KEY="fake",
    )
    return _assemble(
        cfg,
        auth_provider=FakeAuthProvider(),
        profiles=FakeProfilesRepo(),
        sessions=FakeSessionsRepo(),
        audit=FakeAuditRepo(),
        app_config=FakeAppConfigRepo(),
        documents=FakeDocumentsRepo(),
        model_validator=FakeModelValidator(),
    )


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
def make_user(container):
    """Semeia um usuário diretamente (sem HTTP). role padrão = user."""
    def _make(email="user@agilemind.test", password="senha123", nome="User", role="user"):
        res = container.admin_service.create_user(None, email, nome, password=password, role=role)
        return {"email": email, "password": password, "user_id": res["user_id"], "role": role}

    return _make


@pytest.fixture
def login(client):
    def _login(email, password):
        r = client.post("/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.get_json()
        return client

    return _login


@pytest.fixture
def as_admin(client, make_user):
    """Cria um admin, loga e devolve (client, creds)."""
    def _go(email="admin@agilemind.test", password="senha123"):
        u = make_user(email=email, password=password, nome="Admin", role="admin")
        r = client.post("/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.get_json()
        return client, u

    return _go


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"
