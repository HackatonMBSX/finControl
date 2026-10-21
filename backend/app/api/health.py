"""Rotas de infraestrutura: saúde e versão do serviço.

Este arquivo oferece rotas simples para saber se a API está no ar (/health), se o banco responde (/ready) e qual
versão está rodando (/version). A raiz (/) leva ao Swagger quando a documentação está ligada.
Ferramentas como o HEALTHCHECK do Docker e o Coolify chamam essas rotas para monitorar o serviço.
Quem usa: main.py inclui estas rotas no app.
"""

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

log = logging.getLogger("app.health")

router = APIRouter(tags=["infra"])


@router.get("/", include_in_schema=False, response_model=None)
def raiz(request: Request) -> Response:
    """Porta de entrada no navegador: abre o Swagger (se ligado); senão, nome e versão do serviço."""
    s = request.app.state.settings
    if s.enable_docs:
        return RedirectResponse("/docs")
    return JSONResponse({"name": s.app_name, "version": s.app_version})


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: o processo está de pé. Usado pelo HEALTHCHECK do Docker/Coolify."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request, response: Response) -> dict[str, str]:
    """Readiness: dependências (banco) respondem."""
    try:
        ok = request.app.state.repository.ping()
    except Exception:
        log.exception("readiness: o repositório não respondeu")
        ok = False
    if not ok:
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "ready"}


@router.get("/version")
def version(request: Request) -> dict[str, str]:
    """Nome, versão e ambiente do serviço no ar."""
    s = request.app.state.settings
    return {"name": s.app_name, "version": s.app_version, "env": s.app_env}
