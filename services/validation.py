"""Validações reutilizáveis."""
import re

from .errors import ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> str:
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise ValidationError("E-mail inválido")
    return email
