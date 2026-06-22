"""Geração e validação de força de senha."""
from __future__ import annotations

import secrets
import string

from .errors import ValidationError

_LOWER = string.ascii_lowercase
_UPPER = string.ascii_uppercase
_DIGITS = string.digits
_SYMBOLS = "!@#$%&*?-_"


def generate_password(length: int = 16) -> str:
    """Senha forte com ao menos um de cada classe (ADM-15/23)."""
    if length < 8:
        length = 8
    pools = [_LOWER, _UPPER, _DIGITS, _SYMBOLS]
    chars = [secrets.choice(p) for p in pools]
    alphabet = "".join(pools)
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    # Embaralha sem viés.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def validate_strength(password: str, min_len: int) -> None:
    if not password or len(password) < min_len:
        raise ValidationError(f"A senha deve ter ao menos {min_len} caracteres")
