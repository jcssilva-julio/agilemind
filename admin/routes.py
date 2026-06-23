"""
Blueprint de administração. Bootstrap/emergência usam a senha master; todas as
demais rotas exigem sessão com role=admin (revalidado a cada request).
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, g, jsonify, render_template, request

from auth.routes import current_role, current_user_id

bp = Blueprint("admin", __name__)


def _svc():
    return current_app.config["CONTAINER"].admin_service


def _json():
    return request.get_json(silent=True) or {}


def admin_required(view):
    """401 se sem sessão; 403 se a sessão não é de admin (ADM-10/11/12)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        uid = current_user_id()
        if not uid:
            return jsonify({"error": "Não autenticado"}), 401
        if current_role() != "admin":
            return jsonify({"error": "Acesso restrito a administradores"}), 403
        g.user_id = uid
        return view(*args, **kwargs)

    return wrapper


# ── Painel ─────────────────────────────────────────────────────────────
@bp.get("/admin")
@admin_required
def admin_page():
    return render_template("admin.html")


# ── Bootstrap / emergência (senha master) ──────────────────────────────
@bp.get("/admin/setup")
def setup_page():
    # Página pública de primeiro acesso; o POST recusa se já houver admin.
    return render_template("setup.html")


@bp.post("/admin/bootstrap")
def bootstrap():
    d = _json()
    uid = _svc().bootstrap_admin(
        d.get("master_password"), d.get("email"), d.get("password"), d.get("nome")
    )
    return jsonify({"ok": True, "user_id": uid}), 201


@bp.post("/admin/emergency-recovery")
def emergency_recovery():
    d = _json()
    uid = _svc().emergency_recovery(d.get("master_password"))
    return jsonify({"ok": True, "recovered_user_id": uid}), 200


# ── Gestão de usuários ─────────────────────────────────────────────────
@bp.get("/admin/users")
@admin_required
def list_users():
    return jsonify({"users": _svc().list_users()}), 200


@bp.post("/admin/users")
@admin_required
def create_user():
    d = _json()
    res = _svc().create_user(
        g.user_id, d.get("email"), d.get("nome"),
        password=d.get("password"), role=d.get("role", "user"),
        generate=bool(d.get("generate")),
    )
    return jsonify({"ok": True, **res}), 201


@bp.patch("/admin/users/<user_id>")
@admin_required
def update_user(user_id):
    d = _json()
    _svc().update_user(g.user_id, user_id, nome=d.get("nome"), email=d.get("email"))
    return jsonify({"ok": True}), 200


@bp.post("/admin/users/<user_id>/role")
@admin_required
def set_role(user_id):
    _svc().set_role(g.user_id, user_id, _json().get("role"))
    return jsonify({"ok": True}), 200


@bp.post("/admin/users/<user_id>/reset-password")
@admin_required
def reset_password(user_id):
    d = _json()
    res = _svc().reset_password(
        g.user_id, user_id, password=d.get("password"), generate=bool(d.get("generate"))
    )
    return jsonify({"ok": True, **res}), 200


@bp.post("/admin/users/<user_id>/deactivate")
@admin_required
def deactivate_user(user_id):
    _svc().set_active(g.user_id, user_id, False)
    return jsonify({"ok": True}), 200


@bp.post("/admin/users/<user_id>/reactivate")
@admin_required
def reactivate_user(user_id):
    _svc().set_active(g.user_id, user_id, True)
    return jsonify({"ok": True}), 200


@bp.delete("/admin/users/<user_id>")
@admin_required
def delete_user(user_id):
    _svc().delete_user(g.user_id, user_id)
    return jsonify({"ok": True}), 200


# ── Configuração de modelo de IA ───────────────────────────────────────
@bp.get("/admin/model")
@admin_required
def get_model():
    return jsonify(_svc().get_models()), 200


@bp.put("/admin/model")
@admin_required
def set_model():
    d = _json()
    _svc().set_model(g.user_id, d.get("kind"), d.get("model_id"))
    return jsonify({"ok": True}), 200


# ── Documentos (visão administrativa) ──────────────────────────────────
@bp.get("/admin/documents")
@admin_required
def list_documents():
    return jsonify({"documents": _svc().list_documents()}), 200


@bp.delete("/admin/documents/<doc_id>")
@admin_required
def delete_document(doc_id):
    _svc().delete_document(g.user_id, doc_id)
    return jsonify({"ok": True}), 200


@bp.post("/admin/documents/<doc_id>/reindex")
@admin_required
def reindex_document(doc_id):
    from services.errors import DomainError
    try:
        n = _svc().reindex_document(g.user_id, doc_id)
    except DomainError:
        raise  # 4xx tratado pelo handler de domínio
    except Exception:
        # Reindex falhou (ex.: extração/embed). Estado anterior preservado (ADM-30).
        return jsonify({"error": "Falha ao reindexar o documento"}), 500
    return jsonify({"ok": True, "chunks": n}), 200


# ── Auditoria (somente leitura) ────────────────────────────────────────
@bp.get("/admin/audit")
@admin_required
def audit_log():
    return jsonify({"entries": _svc().audit_list()}), 200
