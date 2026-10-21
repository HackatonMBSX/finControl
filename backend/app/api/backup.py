"""Rotas de backup e restauração dos dados da família.

Este arquivo exporta os dados da família num JSON com versão e checksum (uma impressão digital do conteúdo que
denuncia se o arquivo foi alterado), guarda os últimos backups num histórico e restaura a partir de um arquivo.
Antes de restaurar, valida o arquivo inteiro e salva um backup automático do estado atual, para poder voltar atrás.
Quem usa: main.py inclui estas rotas. Conversa com api/dados.py para saber quais coleções e modelos existem.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import ValidationError

from app.api.dados import RECURSOS, ConfigIn, config_id, read_config
from app.api.deps import CurrentUser, get_repository, require_roles
from app.core.errors import AppError, NotFoundError
from app.repositories.base import Doc, Repository

log = logging.getLogger("app.backup")
router = APIRouter(prefix="/api/v1/backup", tags=["backup"])

VERSAO = 1
COLECOES = tuple(RECURSOS)
HISTORICO = "backups"
HISTORICO_MAX = 10
ITENS_MAX = 20_000
admin = require_roles("admin")


def _normalizar(valor: Any) -> Any:
    """Troca números decimais inteiros (como 10.0) por inteiros, em qualquer nível.
    Assim o checksum dá o mesmo resultado mesmo que o JSON tenha sido regravado por outro programa.
    """
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, dict):
        return {k: _normalizar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_normalizar(v) for v in valor]
    return valor


def _checksum(versao: int, dados: dict[str, Any], config: dict[str, Any]) -> str:
    """Calcula o SHA-256 do conteúdo do backup num JSON canônico, com chaves ordenadas."""
    conteudo = _normalizar({"versao": versao, "dados": dados, "config": config})
    canonico = json.dumps(conteudo, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _item(doc: Doc) -> Doc:
    """Tira do documento os campos internos (família e datas) que não vão para o backup."""
    return {k: v for k, v in doc.items() if k not in ("familyId", "createdAt", "updatedAt")}


def _snapshot(repo: Repository, family_id: str) -> dict[str, Any]:
    """Monta o backup atual da família com dados, configurações, data de geração e checksum."""
    dados = {nome: [_item(d) for d in repo.list(nome, family_id)] for nome in COLECOES}
    config = read_config(repo, family_id)
    return {
        "app": "fincontrol",
        "versao": VERSAO,
        "geradoEm": datetime.now(UTC).isoformat(timespec="seconds"),
        "dados": dados,
        "config": config,
        "checksum": _checksum(VERSAO, dados, config),
    }


def _contagens(backup: dict[str, Any]) -> dict[str, int]:
    """Conta quantos itens há em cada coleção do backup."""
    return {nome: len(itens) for nome, itens in backup["dados"].items()}


def _guardar(repo: Repository, family_id: str, backup: dict[str, Any], motivo: str, user_id: str) -> Doc:
    """Salva o backup no histórico e apaga os mais antigos além do limite."""
    doc = repo.create(
        HISTORICO,
        family_id,
        {
            "motivo": motivo,
            "por": user_id,
            "geradoEm": backup["geradoEm"],
            "contagens": _contagens(backup),
            "checksum": backup["checksum"],
            "conteudo": json.dumps(backup, ensure_ascii=False),
        },
    )
    antigos = sorted(repo.list(HISTORICO, family_id), key=lambda d: d["createdAt"])
    for velho in antigos[: max(0, len(antigos) - HISTORICO_MAX)]:
        repo.delete(HISTORICO, family_id, velho["id"])
    return doc


def _resumo(doc: Doc) -> Doc:
    """Devolve só os campos do backup usados na listagem do histórico."""
    return {k: doc.get(k) for k in ("id", "motivo", "geradoEm", "contagens", "checksum")}


def _invalido(msg: str) -> AppError:
    """Cria o erro 422 usado para qualquer problema no arquivo de backup."""
    return AppError(422, "backup_invalido", msg)


def _validar(body: dict[str, Any]) -> tuple[dict[str, list[tuple[str, dict[str, Any]]]], dict[str, Any]]:
    """Confere app, versão, checksum, coleções e cada registro do backup antes de qualquer gravação.
    Devolve os itens validados de cada coleção, com o id original, e as configurações.
    """
    versao = body.get("versao")
    if body.get("app") != "fincontrol" or not isinstance(versao, int):
        raise _invalido("Este arquivo não é um backup do FinControl.")
    if versao != VERSAO:
        raise _invalido(f"Versão {versao} do backup não é suportada (esperada: {VERSAO}).")
    dados, config = body.get("dados"), body.get("config")
    if not isinstance(dados, dict) or not isinstance(config, dict):
        raise _invalido("Backup incompleto: faltam dados ou configurações.")
    if _checksum(versao, dados, config) != body.get("checksum"):
        raise _invalido("O arquivo foi alterado ou está corrompido (checksum não confere).")
    if set(dados) - set(COLECOES):
        raise _invalido("Backup com coleções desconhecidas.")

    total = 0
    validados: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for nome in COLECOES:
        itens = dados.get(nome, [])
        if not isinstance(itens, list):
            raise _invalido(f"Coleção {nome} inválida.")
        total += len(itens)
        if total > ITENS_MAX:
            raise _invalido("Backup grande demais.")
        modelo = RECURSOS[nome][0]
        validados[nome] = []
        for pos, item in enumerate(itens, start=1):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise _invalido(f"{nome} #{pos}: registro sem id.")
            corpo = {k: v for k, v in item.items() if k != "id"}
            try:
                validados[nome].append((item["id"], modelo(**corpo).model_dump(mode="json")))
            except ValidationError as exc:
                raise _invalido(f"{nome} #{pos}: {exc.errors()[0]['msg']}") from exc
    try:
        cfg = ConfigIn(**config).model_dump(mode="json")
    except ValidationError as exc:
        raise _invalido(f"configurações: {exc.errors()[0]['msg']}") from exc
    return validados, cfg


@router.get("")
def exportar(user: CurrentUser = Depends(admin), repo: Repository = Depends(get_repository)) -> dict[str, Any]:
    """Exporta os dados da família em JSON com versão e checksum e registra no histórico."""
    backup = _snapshot(repo, user.family_id)
    _guardar(repo, user.family_id, backup, "exportação manual", user.id)
    return backup


@router.get("/historico")
def historico(user: CurrentUser = Depends(admin), repo: Repository = Depends(get_repository)) -> list[Doc]:
    """Lista os backups guardados (os 10 últimos)."""
    docs = sorted(repo.list(HISTORICO, user.family_id), key=lambda d: d["createdAt"], reverse=True)
    return [_resumo(d) for d in docs]


@router.get("/historico/{backup_id}")
def baixar(
    backup_id: str, user: CurrentUser = Depends(admin), repo: Repository = Depends(get_repository)
) -> dict[str, Any]:
    """Devolve o arquivo de um backup do histórico."""
    doc = repo.get(HISTORICO, user.family_id, backup_id)
    if doc is None:
        raise NotFoundError("Backup")
    conteudo: dict[str, Any] = json.loads(doc["conteudo"])
    return conteudo


@router.post("/restore")
def restaurar(
    body: dict[str, Any] = Body(...),
    user: CurrentUser = Depends(admin),
    repo: Repository = Depends(get_repository),
) -> dict[str, Any]:
    """Substitui os dados da família pelo conteúdo do arquivo. Nada é gravado se o arquivo for inválido."""
    validados, config = _validar(body)
    automatico = _guardar(
        repo, user.family_id, _snapshot(repo, user.family_id), "automático antes de restaurar", user.id
    )
    try:
        for nome in COLECOES:
            for atual in repo.list(nome, user.family_id):
                repo.delete(nome, user.family_id, atual["id"])
        novos: dict[str, str] = {}
        for nome in COLECOES:
            for antigo, corpo in validados[nome]:
                criado = repo.create(nome, user.family_id, corpo)
                if nome == "despesas":
                    novos[antigo] = criado["id"]
        for novo in novos.values():
            doc = repo.get("despesas", user.family_id, novo)
            if doc and doc.get("origemId"):
                repo.update("despesas", user.family_id, novo, {"origemId": novos.get(doc["origemId"], "")})
        cid = config_id(user.family_id)
        if repo.update("configuracoes", user.family_id, cid, config) is None:
            repo.create("configuracoes", user.family_id, config, doc_id=cid)
    except Exception as exc:
        log.exception("restauração falhou no meio")
        raise AppError(
            500,
            "restauracao_falhou",
            "A restauração falhou no meio. O estado anterior está no histórico de backups (automático): "
            "restaure-o para voltar.",
        ) from exc
    log.info("backup restaurado", extra={"family_id": user.family_id, "contagens": _contagens(body)})
    return {"restaurado": _contagens(body), "backupAutomaticoId": automatico["id"]}
