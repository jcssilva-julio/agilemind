"""Erros de domínio que carregam o status HTTP e uma mensagem segura."""


class DomainError(Exception):
    status = 400
    # Mensagem genérica por padrão — nunca vaza detalhes (existência de e-mail etc.)
    message = "Requisição inválida"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class ValidationError(DomainError):
    status = 400


class Unauthorized(DomainError):
    status = 401
    message = "Credenciais inválidas"


class Forbidden(DomainError):
    status = 403
    message = "Acesso negado"


class NotFound(DomainError):
    status = 404
    message = "Não encontrado"


class Conflict(DomainError):
    status = 409
    message = "Já existe"


class RateLimited(DomainError):
    status = 429
    message = "Muitas tentativas. Tente novamente mais tarde."
