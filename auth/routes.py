"""
Rotas de autenticação e o decorator @login_required.

Não há rota de cadastro público (AUTH-14): usuários só nascem em
/admin/create-user, protegida por senha master.
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from services.errors import DomainError, Unauthorized

bp = Blueprint("auth", __name__)


def _svc():
    return current_app.config["CONTAINER"].auth_service


def _cfg():
    return current_app.config["CONTAINER"].config


def _json():
    return request.get_json(silent=True) or {}


def login_required(view):
    """Exige sessão válida; injeta g.user_id. Caso contrário, 401."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(_cfg().SESSION_COOKIE)
        user_id = _svc().resolve(token)
        if not user_id:
            return jsonify({"error": "Não autenticado"}), 401
        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapper


@bp.errorhandler(DomainError)
def _handle_domain_error(e: DomainError):
    return jsonify({"error": e.message}), e.status


@bp.post("/admin/create-user")
def create_user():
    d = _json()
    user_id = _svc().create_user(
        d.get("master_password"), d.get("email"), d.get("password"), d.get("nome")
    )
    # Nunca retorna a senha master nem a senha do usuário (AUTH-01).
    return jsonify({"ok": True, "user_id": user_id}), 201


@bp.post("/admin/deactivate-user")
def deactivate_user():
    d = _json()
    _svc().deactivate_user(d.get("master_password"), d.get("email"))
    return jsonify({"ok": True}), 200


@bp.post("/login")
def login():
    d = _json()
    token = _svc().login(d.get("email"), d.get("password"))
    resp = jsonify({"ok": True})
    resp.set_cookie(
        _cfg().SESSION_COOKIE,
        token,
        httponly=True,
        samesite="Lax",
        secure=not current_app.debug,
    )
    return resp, 200


@bp.post("/logout")
@login_required
def logout():
    token = request.cookies.get(_cfg().SESSION_COOKIE)
    _svc().logout(token)
    resp = jsonify({"ok": True})
    resp.delete_cookie(_cfg().SESSION_COOKIE)
    return resp, 200
