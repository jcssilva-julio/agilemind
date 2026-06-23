"""
Camada de Administração v2 — casos ADM-01..47.
ADM-28..31 (documentos) ficam deferidos para depois das Fases 3/4.
Ver tests/casos_de_teste_admin.md.
"""
import pytest


def _token(resp):
    for c in resp.headers.getlist("Set-Cookie"):
        if c.startswith("agilemind_session="):
            return c.split("=", 1)[1].split(";", 1)[0]
    return None


# ═══════════════ 5.1 Bootstrap e emergência ═══════════════
def test_adm_01_bootstrap_primeiro_admin(client, master, container):
    r = client.post("/admin/bootstrap", json={
        "master_password": master, "email": "adm@x.com", "password": "senha123", "nome": "Adm"})
    assert r.status_code == 201
    uid = r.get_json()["user_id"]
    p = container.profiles.get(uid)
    assert p["role"] == "admin" and p["created_by"] is None
    assert any(e["action"] == "bootstrap_admin" for e in container.audit.entries)


def test_adm_02_bootstrap_master_incorreta(client, container):
    r = client.post("/admin/bootstrap", json={
        "master_password": "errada", "email": "a@x.com", "password": "senha123", "nome": "A"})
    assert r.status_code == 401
    assert container.profiles.count_admins(only_active=False) == 0


def test_adm_03_bootstrap_quando_ja_existe_admin(client, master):
    client.post("/admin/bootstrap", json={
        "master_password": master, "email": "a@x.com", "password": "senha123", "nome": "A"})
    r = client.post("/admin/bootstrap", json={
        "master_password": master, "email": "b@x.com", "password": "senha123", "nome": "B"})
    assert r.status_code == 409


def test_adm_04_emergencia_sem_admin_ativo(client, master, make_user, container):
    u = make_user(email="adm@x.com", role="admin")
    container.profiles.set_active(u["user_id"], False)  # nenhum admin ativo
    r = client.post("/admin/emergency-recovery", json={"master_password": master})
    assert r.status_code == 200
    assert container.profiles.is_active(u["user_id"])
    assert any(e["action"] == "emergency_recovery" for e in container.audit.entries)


def test_adm_05_emergencia_master_incorreta(client, make_user, container):
    u = make_user(email="adm@x.com", role="admin")
    container.profiles.set_active(u["user_id"], False)
    r = client.post("/admin/emergency-recovery", json={"master_password": "errada"})
    assert r.status_code == 401
    assert not container.profiles.is_active(u["user_id"])


def test_adm_06_emergencia_havendo_admin_ativo(client, master, make_user):
    make_user(email="adm@x.com", role="admin")  # admin ativo
    r = client.post("/admin/emergency-recovery", json={"master_password": master})
    assert r.status_code == 409


def test_adm_07_master_nunca_em_log_ou_resposta(client, master, container):
    r = client.post("/admin/bootstrap", json={
        "master_password": master, "email": "a@x.com", "password": "senha123", "nome": "A"})
    assert master not in r.get_data(as_text=True)
    assert master not in str(container.audit.entries)


# ═══════════════ 5.2 Login e controle por role ═══════════════
def test_adm_08_login_admin_indica_role(client, make_user):
    u = make_user(email="adm@x.com", role="admin")
    r = client.post("/login", json={"email": u["email"], "password": u["password"]})
    assert r.status_code == 200 and r.get_json()["role"] == "admin"


def test_adm_09_login_user_comum(client, make_user):
    u = make_user(email="user@x.com", role="user")
    r = client.post("/login", json={"email": u["email"], "password": u["password"]})
    assert r.status_code == 200 and r.get_json()["role"] == "user"


def test_adm_10_user_comum_acessa_rota_admin(client, make_user):
    u = make_user(email="user@x.com", role="user")
    client.post("/login", json={"email": u["email"], "password": u["password"]})
    assert client.get("/admin/users").status_code == 403
    assert client.get("/admin").status_code == 403


def test_adm_11_nao_autenticado_acessa_admin(client):
    assert client.get("/admin/users").status_code == 401


def test_adm_12_admin_revogado_perde_acesso(as_admin, container):
    client, admin = as_admin()
    assert client.get("/admin/users").status_code == 200
    container.profiles.set_role(admin["user_id"], "user")  # revoga
    assert client.get("/admin/users").status_code == 403  # revalidado no request seguinte


# ═══════════════ 5.3 Administração de usuários ═══════════════
def test_adm_13_listar_usuarios_sem_hash(as_admin, make_user):
    client, _ = as_admin()
    make_user(email="alvo@x.com")
    r = client.get("/admin/users")
    assert r.status_code == 200
    users = r.get_json()["users"]
    assert any(u["email"] == "alvo@x.com" for u in users)
    assert "password" not in str(users) and "hash" not in str(users).lower()


def test_adm_14_criar_usuario_senha_manual(as_admin, app):
    client, _ = as_admin()
    r = client.post("/admin/users", json={
        "email": "novo@x.com", "nome": "Novo", "password": "senha123", "role": "user"})
    assert r.status_code == 201
    c2 = app.test_client()
    assert c2.post("/login", json={"email": "novo@x.com", "password": "senha123"}).status_code == 200


def test_adm_15_criar_usuario_senha_gerada(as_admin, app):
    client, _ = as_admin()
    r = client.post("/admin/users", json={"email": "gen@x.com", "nome": "Gen", "generate": True})
    assert r.status_code == 201
    pwd = r.get_json()["password"]
    assert pwd and len(pwd) >= 16
    c2 = app.test_client()
    assert c2.post("/login", json={"email": "gen@x.com", "password": pwd}).status_code == 200


def test_adm_16_criar_email_existente(as_admin, make_user):
    client, _ = as_admin()
    make_user(email="dup@x.com")
    r = client.post("/admin/users", json={"email": "dup@x.com", "nome": "D", "password": "senha123"})
    assert r.status_code == 409


def test_adm_17_editar_nome_email(as_admin, make_user, container):
    client, _ = as_admin()
    u = make_user(email="edit@x.com")
    r = client.patch(f"/admin/users/{u['user_id']}", json={"nome": "Novo Nome", "email": "edit2@x.com"})
    assert r.status_code == 200
    assert container.profiles.get(u["user_id"])["nome"] == "Novo Nome"
    assert container.auth_provider.get_email(u["user_id"]) == "edit2@x.com"


def test_adm_18_promover_para_admin(as_admin, make_user, container):
    client, _ = as_admin()
    u = make_user(email="prom@x.com", role="user")
    assert client.post(f"/admin/users/{u['user_id']}/role", json={"role": "admin"}).status_code == 200
    assert container.profiles.get_role(u["user_id"]) == "admin"


def test_adm_19_revogar_admin(as_admin, make_user, container):
    client, _ = as_admin()
    b = make_user(email="b@x.com", role="admin")  # há 2 admins
    assert client.post(f"/admin/users/{b['user_id']}/role", json={"role": "user"}).status_code == 200
    assert container.profiles.get_role(b["user_id"]) == "user"


def test_adm_20_unico_admin_nao_rebaixa_a_si(as_admin):
    client, admin = as_admin()
    r = client.post(f"/admin/users/{admin['user_id']}/role", json={"role": "user"})
    assert r.status_code == 409


def test_adm_21_rebaixar_a_si_havendo_outros(as_admin, make_user):
    client, admin = as_admin()
    make_user(email="b@x.com", role="admin")  # outro admin existe
    assert client.post(f"/admin/users/{admin['user_id']}/role", json={"role": "user"}).status_code == 200
    assert client.get("/admin/users").status_code == 403  # perde acesso


def test_adm_22_reset_senha_manual(as_admin, make_user, app):
    client, _ = as_admin()
    u = make_user(email="rst@x.com", password="senha123")
    r = client.post(f"/admin/users/{u['user_id']}/reset-password", json={"password": "novasenha9"})
    assert r.status_code == 200
    c2 = app.test_client()
    assert c2.post("/login", json={"email": "rst@x.com", "password": "novasenha9"}).status_code == 200
    assert c2.post("/login", json={"email": "rst@x.com", "password": "senha123"}).status_code == 401


def test_adm_23_reset_senha_gerada(as_admin, make_user, app):
    client, _ = as_admin()
    u = make_user(email="rstg@x.com")
    r = client.post(f"/admin/users/{u['user_id']}/reset-password", json={"generate": True})
    pwd = r.get_json()["password"]
    assert len(pwd) >= 16
    c2 = app.test_client()
    assert c2.post("/login", json={"email": "rstg@x.com", "password": pwd}).status_code == 200


def test_adm_24_desativar_usuario(as_admin, make_user, app):
    client, _ = as_admin()
    u = make_user(email="off@x.com", password="senha123")
    assert client.post(f"/admin/users/{u['user_id']}/deactivate").status_code == 200
    c2 = app.test_client()
    assert c2.post("/login", json={"email": "off@x.com", "password": "senha123"}).status_code == 401


def test_adm_25_reativar_usuario(as_admin, make_user, app):
    client, _ = as_admin()
    u = make_user(email="on@x.com", password="senha123")
    client.post(f"/admin/users/{u['user_id']}/deactivate")
    assert client.post(f"/admin/users/{u['user_id']}/reactivate").status_code == 200
    c2 = app.test_client()
    assert c2.post("/login", json={"email": "on@x.com", "password": "senha123"}).status_code == 200


def test_adm_26_excluir_bloqueado_com_documentos(as_admin, make_user, container):
    client, _ = as_admin()
    u = make_user(email="dono@x.com")
    container.documents.counts[u["user_id"]] = 2
    assert client.delete(f"/admin/users/{u['user_id']}").status_code == 409
    container.documents.counts[u["user_id"]] = 0
    assert client.delete(f"/admin/users/{u['user_id']}").status_code == 200


def test_adm_27_admin_nao_exclui_a_si(as_admin):
    client, admin = as_admin()
    assert client.delete(f"/admin/users/{admin['user_id']}").status_code == 403


# ═══════════════ 5.4 Documentos (visão administrativa) ═══════════════
def _seed_doc(container, owner_id, alias, visibility="private", chunks=2):
    did = container.documents.create(owner_id, alias, f"{alias}.pdf", f"p/{alias}", visibility)
    container.chunks.create_many(
        did, [{"chunk_index": i, "content": f"c{i}", "embedding": [1.0, 1.0]} for i in range(chunks)], "m")
    return did


def test_adm_28_ver_todos_documentos(as_admin, make_user, container):
    client, admin = as_admin()
    b = make_user(email="b@x.com")
    _seed_doc(container, admin["user_id"], "DoAdmin", "private")
    _seed_doc(container, b["user_id"], "DoB", "private")  # privado de outro
    docs = client.get("/admin/documents").get_json()["documents"]
    aliases = [d["alias"] for d in docs]
    # Admin vê TODOS, inclusive privados de outros, com dono e chunks.
    assert "DoAdmin" in aliases and "DoB" in aliases
    dob = next(d for d in docs if d["alias"] == "DoB")
    assert dob["owner_email"] == "b@x.com" and dob["chunks"] == 2


def test_adm_29_forcar_reindexacao(as_admin, make_user, container, monkeypatch):
    client, _ = as_admin()
    b = make_user(email="b@x.com")
    did = _seed_doc(container, b["user_id"], "DoB", "private", chunks=2)
    container.storage.files[f"p/DoB"] = b"%PDF"
    monkeypatch.setattr("services.rag.extract_pdf_text", lambda d: "sprint velocity " * 60)
    r = client.post(f"/admin/documents/{did}/reindex")
    assert r.status_code == 200 and r.get_json()["chunks"] >= 1


def test_adm_30_reindexacao_falha_atomica(as_admin, make_user, container, monkeypatch):
    client, _ = as_admin()
    b = make_user(email="b@x.com")
    did = _seed_doc(container, b["user_id"], "DoB", "private", chunks=3)
    container.storage.files["p/DoB"] = b"%PDF"
    monkeypatch.setattr("services.rag.extract_pdf_text", lambda d: "x " * 50)
    # embed falha → não pode perder os chunks antigos.
    def boom(chunks): raise RuntimeError("falha embed")
    monkeypatch.setattr(container.ai, "embed_documents", boom)
    r = client.post(f"/admin/documents/{did}/reindex")
    assert r.status_code >= 400
    assert container.chunks.count_by_document(did) == 3  # estado anterior preservado


def test_adm_31_excluir_doc_de_qualquer_usuario(as_admin, make_user, container):
    client, _ = as_admin()
    b = make_user(email="b@x.com")
    did = _seed_doc(container, b["user_id"], "DoB", "private")
    assert client.delete(f"/admin/documents/{did}").status_code == 200
    assert container.documents.get(did) is None
    assert any(e["action"] == "admin_delete_document" for e in container.audit.entries)


# ═══════════════ 5.5 Configuração de modelo de IA ═══════════════
def test_adm_32_ver_modelo_atual(as_admin):
    client, _ = as_admin()
    r = client.get("/admin/model")
    assert r.status_code == 200
    body = r.get_json()
    assert body["claude_model"] and body["voyage_model"]


def test_adm_33_alterar_modelo_chat(as_admin):
    client, _ = as_admin()
    assert client.put("/admin/model", json={"kind": "claude", "model_id": "claude-novo"}).status_code == 200
    assert client.get("/admin/model").get_json()["claude_model"] == "claude-novo"


def test_adm_34_alterar_modelo_embeddings(as_admin):
    client, _ = as_admin()
    assert client.put("/admin/model", json={"kind": "voyage", "model_id": "voyage-novo"}).status_code == 200
    assert client.get("/admin/model").get_json()["voyage_model"] == "voyage-novo"


def test_adm_35_modelo_invalido_rejeitado(as_admin):
    client, _ = as_admin()
    r = client.put("/admin/model", json={"kind": "claude", "model_id": "modelo-inexistente"})
    assert r.status_code == 400


def test_adm_36_funciona_sem_config(as_admin, container):
    client, _ = as_admin()
    assert container.app_config.get("claude_model") is None  # app_config vazio
    assert client.get("/admin/model").status_code == 200  # usa fallback, sem erro


# ═══════════════ 5.6 Troca de senha pelo próprio usuário ═══════════════
def test_adm_37_trocar_senha_correto(login, make_user):
    u = make_user(email="u@x.com", password="senha123")
    client = login(u["email"], "senha123")
    r = client.post("/account/change-password", json={
        "current_password": "senha123", "new_password": "novasenha9", "confirm_password": "novasenha9"})
    assert r.status_code == 200


def test_adm_38_senha_atual_incorreta(login, make_user):
    u = make_user(email="u@x.com", password="senha123")
    client = login(u["email"], "senha123")
    r = client.post("/account/change-password", json={
        "current_password": "errada", "new_password": "novasenha9", "confirm_password": "novasenha9"})
    assert r.status_code == 401


def test_adm_39_nova_e_confirmacao_diferentes(login, make_user):
    u = make_user(email="u@x.com", password="senha123")
    client = login(u["email"], "senha123")
    r = client.post("/account/change-password", json={
        "current_password": "senha123", "new_password": "novasenha9", "confirm_password": "outra9999"})
    assert r.status_code == 400


def test_adm_40_nova_igual_atual(login, make_user):
    u = make_user(email="u@x.com", password="senha123")
    client = login(u["email"], "senha123")
    r = client.post("/account/change-password", json={
        "current_password": "senha123", "new_password": "senha123", "confirm_password": "senha123"})
    assert r.status_code == 400


def test_adm_41_nova_fraca(login, make_user):
    u = make_user(email="u@x.com", password="senha123")
    client = login(u["email"], "senha123")
    r = client.post("/account/change-password", json={
        "current_password": "senha123", "new_password": "123", "confirm_password": "123"})
    assert r.status_code == 400


def test_adm_42_sessoes_invalidadas_apos_troca(login, make_user):
    u = make_user(email="u@x.com", password="senha123")
    client = login(u["email"], "senha123")
    token = None
    r = client.post("/login", json={"email": u["email"], "password": "senha123"})
    for c in r.headers.getlist("Set-Cookie"):
        if c.startswith("agilemind_session="):
            token = c.split("=", 1)[1].split(";", 1)[0]
    client.post("/account/change-password", json={
        "current_password": "senha123", "new_password": "novasenha9", "confirm_password": "novasenha9"})
    r2 = client.get("/me", headers={"Cookie": f"agilemind_session={token}"})
    assert r2.status_code == 401


def test_adm_43_user_comum_troca_propria_senha(login, make_user):
    u = make_user(email="comum@x.com", password="senha123", role="user")
    client = login(u["email"], "senha123")
    r = client.post("/account/change-password", json={
        "current_password": "senha123", "new_password": "novasenha9", "confirm_password": "novasenha9"})
    assert r.status_code == 200


def test_adm_44_admin_troca_propria_senha(as_admin):
    client, admin = as_admin()
    r = client.post("/account/change-password", json={
        "current_password": admin["password"], "new_password": "novasenha9", "confirm_password": "novasenha9"})
    assert r.status_code == 200


# ═══════════════ 5.7 Auditoria ═══════════════
def test_adm_45_acao_gera_log(as_admin, container):
    client, admin = as_admin()
    antes = len(container.audit.entries)
    client.post("/admin/users", json={"email": "log@x.com", "nome": "L", "password": "senha123"})
    assert len(container.audit.entries) > antes
    ultima = container.audit.entries[-1]
    assert ultima["actor_user_id"] == admin["user_id"] and ultima["action"] == "create_user"


def test_adm_46_log_somente_leitura(as_admin):
    client, _ = as_admin()
    assert client.get("/admin/audit").status_code == 200
    # Não existe escrita/exclusão de auditoria.
    assert client.post("/admin/audit", json={}).status_code == 405
    assert client.delete("/admin/audit").status_code == 405


def test_adm_47_user_comum_nao_acessa_auditoria(client, make_user):
    u = make_user(email="user@x.com", role="user")
    client.post("/login", json={"email": u["email"], "password": u["password"]})
    assert client.get("/admin/audit").status_code == 403
