"""
Camada de administração: bootstrap/emergência (senha master), gestão de
usuários, configuração de modelo de IA. Toda ação relevante grava auditoria.

Regras de invariante:
- O sistema nunca pode ficar sem admin ativo por ação direta (ADM-20).
- Master só no bootstrap (sem nenhum admin) e na emergência (nenhum admin ativo).
"""
from __future__ import annotations

import secrets

from services.errors import Conflict, Forbidden, NotFound, Unauthorized, ValidationError
from services.passwords import generate_password, validate_strength
from services.validation import normalize_email, validate_email

CLAUDE_KEY = "claude_model"
VOYAGE_KEY = "voyage_model"


class AdminService:
    def __init__(self, config, auth_provider, profiles, sessions, audit,
                 documents, app_config, model_validator):
        self.cfg = config
        self.provider = auth_provider
        self.profiles = profiles
        self.sessions = sessions
        self.audit = audit
        self.documents = documents
        self._app_config = app_config
        self.model_validator = model_validator

    # ── Senha master (bootstrap / emergência) ──────────────────────────
    def _check_master(self, master_password) -> None:
        if master_password is None or master_password == "":
            raise ValidationError("Senha master obrigatória")
        expected = self.cfg.MASTER_PASSWORD or ""
        if not secrets.compare_digest(str(master_password), expected):
            raise Unauthorized()

    def bootstrap_admin(self, master_password, email, password, nome) -> str:
        self._check_master(master_password)
        if self.profiles.count_admins(only_active=False) > 0:
            raise Conflict("Já existe administrador; bootstrap indisponível")  # ADM-03
        email = validate_email(email)
        validate_strength(password, self.cfg.MIN_PASSWORD_LEN)
        uid = self.provider.create_user(email, password)
        self.profiles.create(uid, (nome or "").strip(), role="admin", created_by=None)
        self.audit.log(None, "bootstrap_admin", target_user_id=uid)
        return uid

    def emergency_recovery(self, master_password) -> str:
        self._check_master(master_password)
        if self.profiles.count_admins(only_active=True) > 0:
            raise Conflict("Há admin ativo; recuperação de emergência indisponível")  # ADM-06
        admin = self.profiles.oldest_admin()
        if not admin:
            raise NotFound("Nenhum administrador para recuperar")
        uid = admin["user_id"]
        self.profiles.set_active(uid, True)
        self.audit.log(None, "emergency_recovery", target_user_id=uid)
        return uid

    # ── Gestão de usuários (ações de admin autenticado) ────────────────
    def list_users(self) -> list[dict]:
        emails = {u["id"]: u["email"] for u in self.provider.list_users()}
        out = []
        for p in self.profiles.list_all():
            out.append({
                "user_id": p["user_id"],
                "email": emails.get(p["user_id"]),
                "nome": p.get("nome"),
                "role": p.get("role"),
                "is_active": p.get("is_active"),
                "created_at": p.get("created_at"),
            })  # sem hash de senha (ADM-13)
        return out

    def create_user(self, actor_id, email, nome, password=None, role="user",
                    generate=False) -> dict:
        email = validate_email(email)
        if role not in ("admin", "user"):
            raise ValidationError("Papel inválido")
        if generate or not password:
            password = generate_password(self.cfg.GENERATED_PASSWORD_LEN)
        else:
            validate_strength(password, self.cfg.MIN_PASSWORD_LEN)
        uid = self.provider.create_user(email, password)  # Conflict se duplicado (ADM-16)
        self.profiles.create(uid, (nome or "").strip(), role=role, created_by=actor_id)
        self.audit.log(actor_id, "create_user", target_user_id=uid,
                       details={"role": role, "generated": generate})
        return {"user_id": uid, "password": password if generate else None}

    def update_user(self, actor_id, target_id, nome=None, email=None) -> None:
        self._require_exists(target_id)
        if nome is not None:
            self.profiles.update_nome(target_id, nome.strip())
        if email:
            self.provider.update_email(target_id, validate_email(email))
        self.audit.log(actor_id, "update_user", target_user_id=target_id,
                       details={"nome": nome, "email": bool(email)})

    def set_role(self, actor_id, target_id, role) -> None:
        if role not in ("admin", "user"):
            raise ValidationError("Papel inválido")
        prof = self._require_exists(target_id)
        # Não pode deixar o sistema sem admin ativo (ADM-20).
        if role == "user" and prof.get("role") == "admin":
            if self.profiles.count_admins(only_active=True) <= 1:
                raise Conflict("O sistema não pode ficar sem administrador ativo")
        self.profiles.set_role(target_id, role)
        self.audit.log(actor_id, "set_role", target_user_id=target_id,
                       details={"role": role})

    def reset_password(self, actor_id, target_id, password=None, generate=False) -> dict:
        self._require_exists(target_id)
        if generate or not password:
            password = generate_password(self.cfg.GENERATED_PASSWORD_LEN)
        else:
            validate_strength(password, self.cfg.MIN_PASSWORD_LEN)
        self.provider.update_password(target_id, password)
        self.sessions.delete_by_user(target_id)  # invalida sessões antigas (ADM-22/23)
        self.audit.log(actor_id, "reset_password", target_user_id=target_id,
                       details={"generated": generate})
        return {"password": password if generate else None}

    def set_active(self, actor_id, target_id, active) -> None:
        prof = self._require_exists(target_id)
        # Desativar o último admin ativo deixaria o sistema sem admin.
        if not active and prof.get("role") == "admin":
            if self.profiles.count_admins(only_active=True) <= 1:
                raise Conflict("O sistema não pode ficar sem administrador ativo")
        self.profiles.set_active(target_id, active)
        if not active:
            self.sessions.delete_by_user(target_id)
        self.audit.log(actor_id, "deactivate_user" if not active else "reactivate_user",
                       target_user_id=target_id)

    def delete_user(self, actor_id, target_id) -> None:
        if actor_id == target_id:
            raise Forbidden("Você não pode excluir a própria conta pelo painel")  # ADM-27
        self._require_exists(target_id)
        if self.documents.count_by_owner(target_id) > 0:  # ADM-26: bloquear
            raise Conflict("Usuário possui documentos; trate-os antes de excluir")
        # Log ANTES da exclusão.
        self.audit.log(actor_id, "delete_user", target_user_id=target_id)
        self.sessions.delete_by_user(target_id)
        self.profiles.delete(target_id)
        self.provider.delete_user(target_id)

    def _require_exists(self, user_id) -> dict:
        prof = self.profiles.get(user_id)
        if not prof:
            raise NotFound("Usuário não encontrado")
        return prof

    # ── Configuração de modelo de IA (UC-07) ───────────────────────────
    def get_models(self) -> dict:
        return {
            "claude_model": self.app_config_get(CLAUDE_KEY) or self.cfg.DEFAULT_CLAUDE_MODEL,
            "voyage_model": self.app_config_get(VOYAGE_KEY) or self.cfg.DEFAULT_VOYAGE_MODEL,
        }

    def set_model(self, actor_id, kind, model_id) -> None:
        key = {"claude": CLAUDE_KEY, "voyage": VOYAGE_KEY}.get(kind)
        if not key:
            raise ValidationError("Tipo de modelo desconhecido")
        self.model_validator.validate(kind, model_id)  # ADM-35: valida de verdade
        self.app_config_set(key, model_id.strip(), actor_id)
        self.audit.log(actor_id, "set_model", details={"kind": kind, "model": model_id})

    # app_config helpers (injetado via atributo para manter o construtor enxuto)
    def app_config_get(self, key):
        return self._app_config.get(key)

    def app_config_set(self, key, value, actor_id):
        self._app_config.set(key, value, actor_id)

    # ── Auditoria ──────────────────────────────────────────────────────
    def audit_list(self, limit=200) -> list[dict]:
        return self.audit.list(limit)
