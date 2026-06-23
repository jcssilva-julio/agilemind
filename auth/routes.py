"""
Rotas de autenticação do dia a dia: tela e API de login, logout, /me e troca
de senha pelo próprio usuário. Também expõe os helpers de sessão/role usados
pelos outros blueprints.

Criação/gestão de usuários fica no blueprint de administração (admin/routes.py).
Não há cadastro público (AUTH-14).
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, g, jsonify, render_template, request

from services.errors import DomainError

bp = Blueprint("auth", __name__)


def _container():
    return current_app.config["CONTAINER"]


def _svc():
    return _container().auth_service


def _cfg():
    return _container().config


def _profiles():
    return _container().profiles


def current_user_id():
    """user_id da sessão do cookie atual, ou None. Identidade vem SÓ do token."""
    token = request.cookies.get(_cfg().SESSION_COOKIE)
    return _svc().resolve(token)


def current_role():
    """role do usuário atual (revalidado a cada request — ADM-12), ou None."""
    uid = current_user_id()
    return _profiles().get_role(uid) if uid else None


def _json():
    return request.get_json(silent=True) or {}


def login_required(view):
    """Exige sessão válida; injeta g.user_id. Caso contrário, 401."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user_id = current_user_id()
        if not user_id:
            return jsonify({"error": "Não autenticado"}), 401
        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapper


@bp.errorhandler(DomainError)
def _handle_domain_error(e: DomainError):
    return jsonify({"error": e.message}), e.status


@bp.get("/login")
def login_page():
    if current_user_id():
        return current_app.redirect("/")
    return render_template("login.html")


@bp.post("/login")
def login():
    d = _json()
    token = _svc().login(d.get("email"), d.get("password"))
    role = _profiles().get_role(_svc().resolve(token))
    resp = jsonify({"ok": True, "role": role})  # ADM-08/09
    resp.set_cookie(
        _cfg().SESSION_COOKIE, token,
        httponly=True, samesite="Lax", secure=not current_app.debug,
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


@bp.get("/me")
@login_required
def me():
    # Identidade e role vêm do token/servidor, nunca do payload (AUTH-24).
    c = _container()
    return jsonify({
        "user_id": g.user_id,
        "role": c.profiles.get_role(g.user_id),
        "nome": c.profiles.get_nome(g.user_id),
        "email": c.auth_provider.get_email(g.user_id),
    })


@bp.post("/account/change-password")
@login_required
def change_password():
    d = _json()
    _svc().change_password(
        g.user_id, d.get("current_password"), d.get("new_password"), d.get("confirm_password")
    )
    # Sessões foram invalidadas; limpa o cookie atual também.
    resp = jsonify({"ok": True})
    resp.delete_cookie(_cfg().SESSION_COOKIE)
    return resp, 200
