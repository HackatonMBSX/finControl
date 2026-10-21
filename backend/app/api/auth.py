"""Rotas de cadastro, login e gestão de usuários da família.

Este arquivo cria uma família com seu primeiro usuário (admin), faz o login com e-mail e senha e devolve um token
JWT, mostra os dados do usuário logado e deixa o admin listar, criar e excluir usuários da família.
Para dificultar ataques de adivinhação de senha, cada e-mail pode errar a senha poucas vezes numa janela de tempo.
Esse controle fica na memória do processo.
Quem usa: main.py inclui estas rotas; api/conta.py reaproveita o limite de tentativas.
"""

import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import CurrentUser, current_user, get_auth, get_repository, require_roles
from app.auth_provider import AuthProvider, EmailInUseError
from app.core.errors import AppError, NotFoundError
from app.core.security import create_token
from app.repositories.base import Doc, Repository

router = APIRouter(prefix="/api/v1", tags=["auth"])

Password = Annotated[str, Field(min_length=8, max_length=128)]
Name = Annotated[str, Field(min_length=2, max_length=80)]

MAX_FAILURES, WINDOW_SECONDS = 5, 15 * 60
_failures: dict[str, list[float]] = {}


class RegisterIn(BaseModel):
    """Dados para criar uma nova família e seu primeiro usuário."""

    familia: Name
    nome: Name
    email: EmailStr
    senha: Password


class LoginIn(BaseModel):
    """E-mail e senha para entrar."""

    email: EmailStr
    senha: str = Field(max_length=128)


class UserIn(BaseModel):
    """Dados de um novo usuário da família e o papel dele."""

    nome: Name
    email: EmailStr
    senha: Password
    papel: Literal["admin", "membro", "leitor"] = "membro"


def _public(u: Doc) -> dict[str, str]:
    """Devolve só os campos do perfil que podem ir para o cliente."""
    return {"id": u["id"], "nome": u["nome"], "email": u["email"], "papel": u["papel"], "familyId": u["familyId"]}


def _session(request: Request, user: Doc) -> dict[str, object]:
    """Gera o token de acesso do usuário e monta a resposta de login."""
    s = request.app.state.settings
    token = create_token(
        s.jwt_secret, s.jwt_expire_minutes, user_id=user["id"], family_id=user["familyId"], role=user["papel"]
    )
    return {"accessToken": token, "tokenType": "bearer", "user": _public(user)}


def _check_rate_limit(key: str) -> None:
    """Descarta falhas antigas e responde 429 se a chave já errou demais dentro da janela de tempo."""
    now = time.time()
    recent = [t for t in _failures.get(key, []) if now - t < WINDOW_SECONDS]
    _failures[key] = recent
    if len(recent) >= MAX_FAILURES:
        raise AppError(429, "too_many_attempts", "Muitas tentativas. Aguarde alguns minutos.")


def _new_profile(repo: Repository, auth: AuthProvider, family_id: str, body: RegisterIn | UserIn, role: str) -> Doc:
    """Cria a conta no provedor e o perfil no banco com o e-mail em minúsculas.
    Se o perfil falhar, apaga a conta para não deixar usuário sem perfil.
    """
    try:
        uid = auth.create_user(body.email.lower(), body.senha, body.nome)
    except EmailInUseError as exc:
        raise AppError(409, "email_in_use", "E-mail já cadastrado.") from exc
    try:
        return repo.create(
            "perfis",
            family_id,
            {"userId": uid, "nome": body.nome, "email": body.email.lower(), "papel": role},
            doc_id=uid,
        )
    except Exception:
        auth.delete_user(uid)
        raise


@router.post("/auth/register", status_code=201)
def register(
    body: RegisterIn,
    request: Request,
    repo: Repository = Depends(get_repository),
    auth: AuthProvider = Depends(get_auth),
) -> dict[str, object]:
    """Cria uma nova família e seu primeiro usuário (admin)."""
    if not request.app.state.settings.allow_registration:
        raise AppError(403, "registration_disabled", "Cadastro desativado.")
    family = repo.create("familias", "_root", {"nome": body.familia})
    try:
        profile = _new_profile(repo, auth, family["id"], body, "admin")
    except Exception:
        repo.delete("familias", "_root", family["id"])
        raise
    return _session(request, profile)


@router.post("/auth/login")
def login(
    body: LoginIn,
    request: Request,
    repo: Repository = Depends(get_repository),
    auth: AuthProvider = Depends(get_auth),
) -> dict[str, object]:
    """Entra com e-mail e senha e devolve o token de acesso (com limite de tentativas)."""
    email = body.email.lower()
    _check_rate_limit(email)
    uid = auth.verify(email, body.senha)
    profile = repo.get_any("perfis", uid) if uid else None
    if not profile:
        _failures.setdefault(email, []).append(time.time())
        raise AppError(401, "invalid_credentials", "E-mail ou senha incorretos.")
    _failures.pop(email, None)
    return _session(request, profile)


@router.get("/auth/me")
def me(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)) -> dict[str, str]:
    """Dados do usuário logado."""
    doc = repo.get("perfis", user.family_id, user.id)
    if not doc:
        raise AppError(401, "invalid_token", "Usuário não existe mais.")
    return _public(doc)


@router.get("/usuarios")
def list_users(
    user: CurrentUser = Depends(require_roles("admin")), repo: Repository = Depends(get_repository)
) -> list[dict[str, str]]:
    """Lista os usuários da família."""
    return [_public(u) for u in repo.list("perfis", user.family_id)]


@router.post("/usuarios", status_code=201)
def create_user(
    body: UserIn,
    user: CurrentUser = Depends(require_roles("admin")),
    repo: Repository = Depends(get_repository),
    auth: AuthProvider = Depends(get_auth),
) -> dict[str, str]:
    """Cria um usuário na família com o papel informado."""
    return _public(_new_profile(repo, auth, user.family_id, body, body.papel))


@router.delete("/usuarios/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    user: CurrentUser = Depends(require_roles("admin")),
    repo: Repository = Depends(get_repository),
    auth: AuthProvider = Depends(get_auth),
) -> None:
    """Exclui um usuário da família (não é possível excluir a si mesmo)."""
    if user_id == user.id:
        raise AppError(409, "cannot_delete_self", "Você não pode excluir o próprio usuário.")
    if not repo.delete("perfis", user.family_id, user_id):
        raise NotFoundError("Usuário")
    auth.delete_user(user_id)
