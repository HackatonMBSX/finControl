"""Dependências compartilhadas pelas rotas.

No FastAPI, uma dependência é uma função que roda antes da rota e entrega algo pronto para ela, como o banco
ou o usuário logado. Este arquivo entrega o repositório e o provedor de login guardados no app, descobre quem é
o usuário a partir do token JWT enviado no cabeçalho Authorization e barra quem não tem o papel exigido.
Os papéis possíveis são admin, membro e leitor.
Quem usa: todos os arquivos de rotas em api/.
"""

from collections.abc import Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth_provider import AuthProvider
from app.core.errors import AppError, ForbiddenError
from app.core.security import decode_token
from app.repositories.base import Repository

bearer = HTTPBearer(auto_error=False)

ROLES = ("admin", "membro", "leitor")


@dataclass(frozen=True)
class CurrentUser:
    """Usuário logado, com id, família e papel tirados do token."""

    id: str
    family_id: str
    role: str


def get_repository(request: Request) -> Repository:
    """Devolve o repositório de dados guardado no app."""
    repo: Repository = request.app.state.repository
    return repo


def get_auth(request: Request) -> AuthProvider:
    """Devolve o provedor de autenticação guardado no app."""
    auth: AuthProvider = request.app.state.auth
    return auth


def current_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    """Lê o token Bearer e devolve o usuário logado; responde 401 sem token, com token inválido
    ou quando o perfil não existe mais na família.
    """
    if creds is None:
        raise AppError(401, "unauthenticated", "Faça login para continuar.")
    try:
        claims = decode_token(request.app.state.settings.jwt_secret, creds.credentials)
    except jwt.PyJWTError as exc:
        raise AppError(401, "invalid_token", "Sessão inválida ou expirada.") from exc
    repo: Repository = request.app.state.repository
    if repo.get("perfis", claims["fam"], claims["sub"]) is None:
        raise AppError(401, "invalid_token", "Sessão inválida ou expirada.")
    return CurrentUser(id=claims["sub"], family_id=claims["fam"], role=claims["role"])


def require_roles(*allowed: str) -> Callable[[CurrentUser], CurrentUser]:
    """Cria uma dependência que só deixa passar usuários com um dos papéis informados."""

    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        """Devolve o usuário logado ou responde 403 se o papel dele não estiver na lista."""
        if user.role not in allowed:
            raise ForbiddenError()
        return user

    return dep
