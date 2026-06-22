"""
Seção 3 — Autenticação e senha master.

Estado-alvo (Railway + Supabase Auth). Os testes nascem skipped: o código
correspondente ainda não existe no app.py atual. Remova o skip ao implementar
cada caso (TDD: faça falhar primeiro, depois codamos até passar).

Casos: AUTH-01 .. AUTH-24 — ver tests/casos_de_teste.md (seção 3).
"""
import pytest

pytestmark = pytest.mark.skip(reason="TDD: auth (Supabase + senha master) ainda não implementada")


# 3.1 Criação de usuário via senha master
def test_auth_01_criar_usuario_com_master_correta(client):
    """201; usuário em Auth + profiles; senha master não vaza na resposta."""
    raise NotImplementedError


def test_auth_02_master_incorreta(client):
    """401; nenhum usuário criado; mensagem genérica."""
    raise NotImplementedError


def test_auth_03_sem_master(client):
    """400; nenhum usuário criado."""
    raise NotImplementedError


def test_auth_04_email_ja_existente(client):
    """409; nenhum novo registro."""
    raise NotImplementedError


def test_auth_05_email_invalido(client):
    """400; validação antes de chamar o Supabase."""
    raise NotImplementedError


def test_auth_06_senha_fraca(client):
    """400; senha < 6 caracteres rejeitada."""
    raise NotImplementedError


def test_auth_07_exige_https_em_producao(client):
    """Redireciona p/ HTTPS ou bloqueia HTTP puro."""
    raise NotImplementedError


def test_auth_08_master_nunca_em_logs(client):
    """Nenhuma ocorrência da senha master em texto plano nos logs."""
    raise NotImplementedError


def test_auth_09_master_vem_de_env(client):
    """Senha master vem de variável de ambiente, nunca hardcoded."""
    raise NotImplementedError


# 3.2 Login
def test_auth_10_login_credenciais_validas(client):
    """200; retorna sessão/token válido."""
    raise NotImplementedError


def test_auth_11_login_senha_incorreta(client):
    """401; mensagem genérica."""
    raise NotImplementedError


def test_auth_12_login_email_inexistente(client):
    """401; mesma mensagem genérica do AUTH-11."""
    raise NotImplementedError


def test_auth_13_login_campos_vazios(client):
    """400."""
    raise NotImplementedError


def test_auth_14_sem_self_signup_publico(client):
    """Não existe rota de registro público; só /admin/create-user."""
    raise NotImplementedError


def test_auth_15_rate_limiting_login(client):
    """Bloqueio temporário após 5 tentativas erradas (janela ~15 min)."""
    raise NotImplementedError


# 3.3 Sessão e proteção de rotas
def test_auth_16_upload_sem_auth(client):
    """401; upload não processado."""
    raise NotImplementedError


def test_auth_17_chat_sem_auth(client):
    """401."""
    raise NotImplementedError


def test_auth_18_pdf_indices_sem_auth(client):
    """401."""
    raise NotImplementedError


def test_auth_19_pdf_load_sem_auth(client):
    """401."""
    raise NotImplementedError


def test_auth_20_pdf_delete_sem_auth(client):
    """401."""
    raise NotImplementedError


def test_auth_21_index_sem_sessao_redireciona_login(client):
    """GET / sem sessão redireciona p/ login, não renderiza o chat."""
    raise NotImplementedError


def test_auth_22_sessao_expirada_rejeitada(client):
    """401; força novo login."""
    raise NotImplementedError


def test_auth_23_logout_encerra_sessao(client):
    """Após /logout, reutilizar o cookie dá 401."""
    raise NotImplementedError


def test_auth_24_token_de_outro_usuario(client):
    """Usuário identificado pelo token, nunca por campo do payload."""
    raise NotImplementedError


# 3.4 Gestão de usuários pós-criação (só via senha master)
def test_auth_25_desativar_usuario_via_master(client):
    """200; usuário marcado como inativo; senha master não vaza."""
    raise NotImplementedError


def test_auth_26_usuario_desativado_nao_loga(client):
    """401; sessão não criada para usuário desativado."""
    raise NotImplementedError
