"""Rotas da integração com o Asaas.

O Asaas é um serviço de cobranças. Este arquivo guarda, por família, o ambiente (sandbox ou produção) e a chave de
API do Asaas. A chave é cifrada antes de ir para o banco e só volta ao cliente mascarada, com os 4 últimos
caracteres. Nesta versão a conexão real com o Asaas ainda não existe: o teste só confere se há chave salva.
Quem usa: main.py inclui estas rotas. Conversa com core/secrets.py para cifrar a chave.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, current_user, get_repository, require_roles
from app.core.secrets import decrypt, encrypt
from app.repositories.base import Doc, Repository

router = APIRouter(prefix="/api/v1/integracoes/asaas", tags=["integracoes"])

COLECAO = "integracoes"


def asaas_doc_id(family_id: str) -> str:
    """Devolve o id fixo do documento de integração do Asaas da família."""
    return f"asaas_{family_id}"


class AsaasIn(BaseModel):
    """Configuração da integração com o Asaas enviada pelo cliente."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    conectado: bool = False
    ambiente: Literal["sandbox", "producao"] = "sandbox"
    apiKey: Annotated[str, Field(max_length=200)] = ""


def _view(doc: Doc | None, secret: str) -> Doc:
    """Monta a resposta sem expor a chave: diz só se há chave e mostra os 4 últimos caracteres."""
    doc = doc or {}
    chave = decrypt(secret, doc["apiKeyCifrada"]) if doc.get("apiKeyCifrada") else None
    return {
        "conectado": bool(doc.get("conectado", False)),
        "ambiente": doc.get("ambiente", "sandbox"),
        "temChave": chave is not None,
        "chaveMascarada": f"••••{chave[-4:]}" if chave else "",
    }


@router.get("")
def obter(
    request: Request, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)
) -> Doc:
    """Configuração do Asaas (ambiente e chave mascarada)."""
    return _view(repo.get(COLECAO, user.family_id, asaas_doc_id(user.family_id)), request.app.state.settings.jwt_secret)


@router.put("")
def salvar(
    body: AsaasIn,
    request: Request,
    user: CurrentUser = Depends(require_roles("admin")),
    repo: Repository = Depends(get_repository),
) -> Doc:
    """Salva ambiente e chave do Asaas (a chave é cifrada; vazia mantém a atual)."""
    secret = request.app.state.settings.jwt_secret
    atual = repo.get(COLECAO, user.family_id, asaas_doc_id(user.family_id))
    data: Doc = {"conectado": body.conectado, "ambiente": body.ambiente}
    if body.apiKey:
        data["apiKeyCifrada"] = encrypt(secret, body.apiKey)
    elif atual and atual.get("apiKeyCifrada"):
        data["apiKeyCifrada"] = atual["apiKeyCifrada"]
    else:
        data["apiKeyCifrada"] = ""
    if atual is None:
        saved = repo.create(COLECAO, user.family_id, data, doc_id=asaas_doc_id(user.family_id))
    else:
        saved = repo.update(COLECAO, user.family_id, asaas_doc_id(user.family_id), data) or data
    return _view(saved, secret)


@router.post("/testar")
def testar(
    request: Request, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)
) -> Doc:
    """Valida a configuração salva. Não chama o Asaas: a integração real está fora do escopo desta versão."""
    cfg = _view(repo.get(COLECAO, user.family_id, asaas_doc_id(user.family_id)), request.app.state.settings.jwt_secret)
    if not cfg["temChave"]:
        return {"ok": False, "mensagem": "Salve uma chave de API antes de testar."}
    return {
        "ok": True,
        "mensagem": (
            f"Configuração completa (ambiente {cfg['ambiente']}). A conexão real com o Asaas ainda não está "
            "ativa: esta tela está preparada para a integração."
        ),
    }
