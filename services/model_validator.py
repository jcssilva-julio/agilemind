"""
Validação de identificadores de modelo via chamada real ao provider (ADM-35).
Injetável: nos testes usamos um fake que não bate na rede.
"""
from __future__ import annotations

from .errors import ValidationError


class RealModelValidator:
    def __init__(self, anthropic_key: str, voyage_key: str):
        self._akey = anthropic_key
        self._vkey = voyage_key

    def validate(self, kind: str, model_id: str) -> None:
        model_id = (model_id or "").strip()
        if not model_id:
            raise ValidationError("Informe o identificador do modelo")
        try:
            if kind == "claude":
                from anthropic import Anthropic
                Anthropic(api_key=self._akey).messages.create(
                    model=model_id, max_tokens=1,
                    messages=[{"role": "user", "content": "ping"}],
                )
            elif kind == "voyage":
                import voyageai
                voyageai.Client(api_key=self._vkey).embed(
                    ["ping"], model=model_id, input_type="query"
                )
            else:
                raise ValidationError("Tipo de modelo desconhecido")
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(f"Modelo '{model_id}' inválido ou indisponível")
