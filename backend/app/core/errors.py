"""Erros da aplicação e formato padrão das respostas de erro.

Este arquivo define os erros que o código lança de propósito (não encontrado, sem permissão etc.) e registra
tratadores no FastAPI para que toda falha volte ao cliente no mesmo formato JSON:
{"error": {"code", "message", "requestId", "details"}}. O requestId ajuda a achar a requisição nos logs.
Erros inesperados viram 500 com mensagem genérica, e o detalhe vai só para o log.
Quem usa: main.py registra os tratadores; api/ e auth_provider.py lançam os erros.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Erro previsto pela aplicação, com status HTTP, código curto e mensagem para o usuário."""

    def __init__(self, status: int, code: str, message: str) -> None:
        """Guarda o status, o código e a mensagem que vão para a resposta."""
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class NotFoundError(AppError):
    """Erro 404 para quando o recurso pedido não existe."""

    def __init__(self, what: str = "Recurso") -> None:
        """Monta a mensagem a partir do nome do recurso que faltou."""
        super().__init__(404, "not_found", f"{what} não encontrado.")


class ForbiddenError(AppError):
    """Erro 403 para quando o usuário não tem permissão para a ação."""

    def __init__(self, message: str = "Sem permissão para esta ação.") -> None:
        """Cria o erro com a mensagem padrão ou com uma mensagem própria."""
        super().__init__(403, "forbidden", message)


def _body(request: Request, code: str, message: str, details: object | None = None) -> dict[str, object]:
    """Monta o corpo JSON do erro, incluindo o id da requisição e detalhes opcionais."""
    err: dict[str, object] = {
        "code": code,
        "message": message,
        "requestId": getattr(request.state, "request_id", None),
    }
    if details is not None:
        err["details"] = details
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    """Liga ao app os tratadores que convertem cada tipo de erro na resposta JSON padrão."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        """Responde com o status, o código e a mensagem do AppError."""
        return JSONResponse(_body(request, exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Converte erros HTTP do Starlette (como 404 de rota) para o formato padrão."""
        return JSONResponse(_body(request, f"http_{exc.status_code}", str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Responde 422 listando cada campo inválido e o motivo, a partir da validação do FastAPI."""
        fields = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body(request, "validation_error", "Dados inválidos.", fields), status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        """Registra no log o erro inesperado e responde 500 sem expor detalhes internos ao cliente."""
        logging.getLogger("app").exception(
            "erro não tratado", extra={"request_id": getattr(request.state, "request_id", None)}
        )
        return JSONResponse(_body(request, "internal_error", "Erro interno."), status_code=500)
