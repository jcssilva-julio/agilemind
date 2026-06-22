"""
Rate limiter de login em memória (AUTH-15): bloqueia após N falhas seguidas
por chave (e-mail), por uma janela de tempo. Em produção com múltiplos workers
o ideal é um backend compartilhado, mas para uma instância é suficiente.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class LoginRateLimiter:
    max_attempts: int = 5
    lockout_seconds: int = 15 * 60
    _state: dict[str, tuple[int, float]] = field(default_factory=dict)
    # injetável para testes determinísticos
    _clock = staticmethod(time.monotonic)

    def is_locked(self, key: str) -> bool:
        count, locked_until = self._state.get(key, (0, 0.0))
        return self._clock() < locked_until

    def register_failure(self, key: str) -> None:
        count, _ = self._state.get(key, (0, 0.0))
        count += 1
        locked_until = self._clock() + self.lockout_seconds if count >= self.max_attempts else 0.0
        self._state[key] = (count, locked_until)

    def reset(self, key: str) -> None:
        self._state.pop(key, None)
