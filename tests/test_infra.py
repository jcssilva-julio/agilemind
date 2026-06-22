"""
Seção 7 — Infraestrutura e deploy (Railway + Supabase).

Casos: INF-01 .. INF-07 — ver tests/casos_de_teste.md (seção 7).
Vários são checagens de ambiente/produção (parte manual), documentadas aqui
para rastreabilidade.
"""
import pytest

pytestmark = pytest.mark.skip(reason="TDD: infraestrutura Railway + Supabase ainda não provisionada")


def test_inf_01_env_vars_presentes(client):
    """ANTHROPIC/VOYAGE/SUPABASE_URL/SUPABASE_KEY/MASTER_PASSWORD/FLASK_SECRET_KEY presentes; nenhuma commitada."""
    raise NotImplementedError


def test_inf_02_app_responde_com_login(client):
    """URL pública retorna tela de login, não o chat direto."""
    raise NotImplementedError


def test_inf_03_conexao_postgres_no_boot(client):
    """Boot sem erros de conexão nos logs."""
    raise NotImplementedError


def test_inf_04_storage_funcional(client):
    """Upload de teste em produção aparece no bucket."""
    raise NotImplementedError


def test_inf_05_limite_plano_gratuito(client):
    """Documentar limite do plano (checagem manual periódica)."""
    raise NotImplementedError


def test_inf_06_bucket_privado(client):
    """URL direta sem auth é negada; só via backend autenticado."""
    raise NotImplementedError


def test_inf_07_https_obrigatorio(client):
    """Railway força HTTPS (confirmar)."""
    raise NotImplementedError
