"""Rotas para excluir a própria conta ou a família inteira.

Este arquivo deixa o usuário logado apagar a própria conta e deixa o admin apagar a família com todos os dados.
As duas ações pedem a senha de novo, para confirmar que é a pessoa mesmo, e usam o mesmo limite de tentativas do
login. O último admin não pode sair sozinho: precisa excluir a família antes.
Quem usa: main.py inclui estas rotas. Conversa com api/auth.py (limite de tentativas) e com o provedor de login.
"""

import logging
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.auth import _check_rate_limit, _failures
from app.api.deps import CurrentUser, current_user, get_auth, get_repository, require_roles
from app.auth_provider import AuthProvider
from app.core.errors import AppError
from app.repositories.base import Repository

log = logging.getLogger("app.conta")
router = APIRouter(prefix="/api/v1", tags=["conta"])

COLECOES_DA_FAMILIA = (
    "despesas", "categorias", "tipos", "bancos", "centros", "configuracoes", "integracoes", "backups",
)  # fmt: skip


class SenhaIn(BaseModel):
    """Senha atual, pedida para confirmar uma exclusão."""

    senha: str = Field(max_length=128)


def _conferir_senha(repo: Repository, auth: AuthProvider, user: CurrentUser, senha: str) -> str:
    """Confere a senha do usuário logado respeitando o limite de tentativas e devolve o e-mail dele.
    Responde 403 se a senha estiver errada.
    """
    perfil = repo.get("perfis", user.family_id, user.id)
    if not perfil:
        raise AppError(401, "invalid_token", "Usuário não existe mais.")
    email = str(perfil["email"])
    _check_rate_limit(email)
    if auth.verify(email, senha) != user.id:
        _failures.setdefault(email, []).append(time.time())
        raise AppError(403, "senha_incorreta", "Senha incorreta.")
    _failures.pop(email, None)
    return email


@router.delete("/conta", status_code=204)
def excluir_minha_conta(
    body: SenhaIn,
    user: CurrentUser = Depends(current_user),
    repo: Repository = Depends(get_repository),
    auth: AuthProvider = Depends(get_auth),
) -> None:
    """Exclui a conta de quem está logado. O último administrador deve excluir a família antes."""
    _conferir_senha(repo, auth, user, body.senha)
    if user.role == "admin":
        admins = [p for p in repo.list("perfis", user.family_id) if p.get("papel") == "admin"]
        if len(admins) <= 1:
            raise AppError(
                409,
                "ultimo_admin",
                "Você é o único administrador. Exclua a família antes de sair.",
            )
    repo.delete("perfis", user.family_id, user.id)
    auth.delete_user(user.id)
    log.info("conta excluída", extra={"family_id": user.family_id})


@router.delete("/familia", status_code=204)
def excluir_familia(
    body: SenhaIn,
    user: CurrentUser = Depends(require_roles("admin")),
    repo: Repository = Depends(get_repository),
    auth: AuthProvider = Depends(get_auth),
) -> None:
    """Exclui a família inteira: despesas, cadastros, configurações, backups e todas as contas dos usuários."""
    _conferir_senha(repo, auth, user, body.senha)
    for colecao in COLECOES_DA_FAMILIA:
        for doc in repo.list(colecao, user.family_id):
            repo.delete(colecao, user.family_id, doc["id"])
    for perfil in repo.list("perfis", user.family_id):
        auth.delete_user(perfil["id"])
        repo.delete("perfis", user.family_id, perfil["id"])
    repo.delete("familias", "_root", user.family_id)
    log.info("família excluída", extra={"family_id": user.family_id})
