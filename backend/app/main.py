"""Ponto de entrada da API.

Este arquivo monta a aplicação FastAPI: lê as configurações, liga os logs, escolhe o banco e o provedor de login,
configura o CORS (quais sites podem chamar a API), registra os tratadores de erro e inclui todas as rotas.
Também adiciona a cada requisição um id único, cabeçalhos de segurança e uma linha de log com status e duração.
Ao iniciar, prepara o banco em segundo plano para que a API não fique esperando por ele.
Quem usa: o uvicorn (comando do Dockerfile carrega app.main:app) e os testes, via create_app.
"""

import logging
import threading
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, backup, conta, dados, health, integracoes
from app.auth_provider import AuthProvider
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.repositories.base import Repository
from app.repositories.factory import build_backends

log = logging.getLogger("app.request")


def _aquecer(warm_up: Callable[[], None], tentativas: int = 5, espera: float = 5.0) -> None:
    """Tenta preparar o banco algumas vezes, com espera entre as tentativas, e só registra no log se falhar."""
    for n in range(1, tentativas + 1):
        try:
            warm_up()
            log.info("banco preparado")
            return
        except Exception:  # noqa: BLE001
            log.warning("preparo do banco falhou (tentativa %s/%s)", n, tentativas, exc_info=True)
            time.sleep(espera)


def create_app(
    settings: Settings | None = None, repository: Repository | None = None, auth_provider: AuthProvider | None = None
) -> FastAPI:
    """Cria e configura a aplicação; repositório e provedor podem ser passados prontos, como nos testes."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Ao subir a API, dispara o preparo do banco numa thread separada, se o repositório oferecer warm_up."""
        warm_up = getattr(app.state.repository, "warm_up", None)
        if warm_up:
            threading.Thread(target=_aquecer, args=(warm_up,), daemon=True).start()
        yield

    app = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings
    default_repo, default_auth = (None, None) if (repository and auth_provider) else build_backends(settings)
    app.state.repository = repository or default_repo
    app.state.auth = auth_provider or default_auth

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Dá um id à requisição (ou reaproveita o X-Request-ID), põe cabeçalhos de segurança e registra o log."""
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        log.info(
            "request",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        return response

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(dados.router)
    app.include_router(integracoes.router)
    app.include_router(backup.router)
    app.include_router(conta.router)
    return app


app = create_app()
