"""
Seção 6 — Gestão de relatórios indexados com visibilidade/permissões (MNG-01..08).
A lógica vive em routes/documents.py. Ver casos_de_teste.md.
"""


def _seed(container, owner_id, alias, visibility):
    return container.documents.create(owner_id, alias, f"{alias}.pdf", f"path/{alias}", visibility)


def test_mng_01_lista_proprios_privados_mais_publicos(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    b = make_user(email="b@x.com", password="senha123")
    _seed(container, a["user_id"], "A-priv", "private")
    _seed(container, a["user_id"], "A-pub", "public")
    b_priv = _seed(container, b["user_id"], "B-priv", "private")
    _seed(container, b["user_id"], "B-pub", "public")
    login(a["email"], "senha123")
    aliases = [d["alias"] for d in client.get("/pdf/indices").get_json()["indices"]]
    assert "A-priv" in aliases and "A-pub" in aliases and "B-pub" in aliases
    assert "B-priv" not in aliases  # privado de outro NÃO aparece
    # e o id do privado de B não vaza
    ids = [d["document_id"] for d in client.get("/pdf/indices").get_json()["indices"]]
    assert b_priv not in ids


def test_mng_02_lista_vazia(client, make_user, login):
    u = make_user(email="novo@x.com", password="senha123")
    login(u["email"], "senha123")
    assert client.get("/pdf/indices").get_json()["indices"] == []


def test_mng_03_carregar_doc_proprio(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = _seed(container, a["user_id"], "Meu", "private")
    login(a["email"], "senha123")
    assert client.post("/pdf/load", json={"document_id": did}).status_code == 200


def test_mng_04_carregar_publico_de_outro(client, make_user, login, container):
    b = make_user(email="b@x.com", password="senha123")
    did = _seed(container, b["user_id"], "Pub", "public")
    a = make_user(email="a@x.com", password="senha123")
    login(a["email"], "senha123")
    assert client.post("/pdf/load", json={"document_id": did}).status_code == 200


def test_mng_05_carregar_privado_de_outro(client, make_user, login, container):
    b = make_user(email="b@x.com", password="senha123")
    did = _seed(container, b["user_id"], "Priv", "private")
    a = make_user(email="a@x.com", password="senha123")
    login(a["email"], "senha123")
    assert client.post("/pdf/load", json={"document_id": did}).status_code == 404  # inexistente p/ A


def test_mng_06_excluir_doc_proprio(client, make_user, login, container):
    a = make_user(email="a@x.com", password="senha123")
    did = _seed(container, a["user_id"], "Meu", "private")
    login(a["email"], "senha123")
    assert client.post("/pdf/delete", json={"document_id": did}).status_code == 200
    assert container.documents.get(did) is None


def test_mng_07_excluir_doc_de_outro(client, make_user, login, container):
    b = make_user(email="b@x.com", password="senha123")
    did = _seed(container, b["user_id"], "DeB", "private")
    a = make_user(email="a@x.com", password="senha123")
    login(a["email"], "senha123")
    assert client.post("/pdf/delete", json={"document_id": did}).status_code == 403
    assert container.documents.get(did) is not None  # nada removido


def test_mng_08_excluir_publico_de_outro(client, make_user, login, container):
    b = make_user(email="b@x.com", password="senha123")
    did = _seed(container, b["user_id"], "PubB", "public")
    a = make_user(email="a@x.com", password="senha123")
    login(a["email"], "senha123")
    # Público dá leitura, não exclusão.
    assert client.post("/pdf/delete", json={"document_id": did}).status_code == 403
