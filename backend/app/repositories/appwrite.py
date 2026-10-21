"""Repositório que guarda os dados no Appwrite.

O Appwrite é o serviço de banco de dados e de contas usado em produção. Este arquivo implementa o contrato de
repositories/base.py em cima dele: cada coleção do app vira uma coleção no Appwrite e todo documento leva o
familyId, usado para separar os dados de cada família.
O banco e as coleções são criados sob demanda na primeira vez que são usados. Leituras e criações são repetidas
algumas vezes quando o Appwrite responde com erro 5xx (falha temporária do servidor).
Quem usa: repositories/factory.py (quando REPOSITORY_BACKEND=appwrite).
"""

import logging
import time
import uuid
from collections.abc import Callable
from functools import partial
from typing import Any

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.query import Query
from appwrite.services.documents_db import DocumentsDB

from app.core.config import Settings
from app.repositories.base import Doc, Repository

log = logging.getLogger("app.appwrite")
PAGE = 100
PROTECTED = {"id", "familyId", "createdAt", "updatedAt"}
COLECOES = (
    "familias", "perfis", "despesas", "categorias", "tipos", "bancos", "centros", "configuracoes", "integracoes",
    "healthcheck",
)  # fmt: skip


def _doc(d: Any) -> Doc:
    """Converte o documento do Appwrite em dicionário com id e datas nos nomes usados pelo app."""
    return {**d.data, "id": d.id, "createdAt": d.createdat, "updatedAt": d.updatedat}


def _clean(data: Doc) -> Doc:
    """Remove campos protegidos e os campos internos do Appwrite (que começam com $) antes de gravar."""
    return {k: v for k, v in data.items() if k not in PROTECTED and not k.startswith("$")}


class AppwriteRepository(Repository):
    """Repositório que lê e grava documentos no banco do Appwrite."""

    def __init__(self, db: DocumentsDB, database_id: str = "fincontrol", retry_delay: float = 3.0) -> None:
        """Guarda o cliente do banco e começa sem nenhuma coleção marcada como pronta."""
        self._db = db
        self._retry_delay = retry_delay
        self._database_id = database_id
        self._database_ready = False
        self._ready: set[str] = set()

    @classmethod
    def from_settings(cls, s: Settings) -> "AppwriteRepository":
        """Cria o repositório com endereço, projeto e chave de API vindos das configurações."""
        client = (
            Client().set_endpoint(s.appwrite_endpoint).set_project(s.appwrite_project_id).set_key(s.appwrite_api_key)
        )
        return cls(DocumentsDB(client), s.appwrite_database_id)

    @staticmethod
    def _conflict(exc: AppwriteException) -> bool:
        """Diz se o erro é 409, ou seja, o item já existe."""
        return bool(exc.code == 409)

    def _criar(self, fn: Callable[[], Any], tentativas: int = 3) -> bool:
        """Executa uma criação, repetindo em erros 5xx; devolve False se o item já existia."""
        for n in range(1, tentativas + 1):
            try:
                fn()
                return True
            except AppwriteException as exc:
                if self._conflict(exc):
                    return False
                if not (exc.code and exc.code >= 500) or n == tentativas:
                    raise
                log.warning("appwrite respondeu %s ao preparar o banco (tentativa %s/%s)", exc.code, n, tentativas)
                time.sleep(self._retry_delay)
        return False

    def _ler(self, fn: Callable[[], Any], tentativas: int = 3) -> Any:
        """Executa uma leitura, repetindo em erros 5xx antes de desistir."""
        for n in range(1, tentativas + 1):
            try:
                return fn()
            except AppwriteException as exc:
                if not (exc.code and exc.code >= 500) or n == tentativas:
                    raise
                log.warning("appwrite respondeu %s numa leitura (tentativa %s/%s)", exc.code, n, tentativas)
                time.sleep(self._retry_delay)

    def warm_up(self) -> None:
        """Prepara de uma vez o banco e todas as coleções conhecidas, para agilizar o primeiro uso."""
        for nome in COLECOES:
            self._ensure(nome)

    def _ensure(self, collection: str) -> None:
        """Garante que o banco e a coleção existem, criando o que faltar.
        Coleções novas ganham um índice por familyId para acelerar as buscas por família.
        """
        if not self._database_ready:
            self._criar(lambda: self._db.create(self._database_id, "FinControl"))
            self._database_ready = True
        if collection in self._ready:
            return
        criou = self._criar(
            lambda: self._db.create_collection(
                self._database_id, collection, collection, permissions=[], document_security=False
            )
        )
        if criou:
            try:
                self._db.create_index(self._database_id, collection, "idx_family", "key", ["familyId"])
            except AppwriteException as exc:
                log.warning("índice por família não criado em %s: %s", collection, exc.message)
        self._ready.add(collection)

    def ping(self) -> bool:
        """Testa o banco criando e apagando um documento de teste na coleção healthcheck."""
        col = "healthcheck"
        self._ensure(col)
        probe = self._db.create_document(self._database_id, col, uuid.uuid4().hex[:20], {"familyId": col})
        self._db.delete_document(self._database_id, col, probe.id)
        return True

    def create(self, collection: str, family_id: str, data: Doc, doc_id: str | None = None) -> Doc:
        """Grava o documento com o familyId; lança ValueError se o id já existir."""
        self._ensure(collection)
        did = doc_id or uuid.uuid4().hex[:20]
        try:
            created = self._db.create_document(
                self._database_id, collection, did, {**_clean(data), "familyId": family_id}
            )
        except AppwriteException as exc:
            if self._conflict(exc):
                raise ValueError(f"documento {did} já existe em {collection}") from exc
            raise
        return _doc(created)

    def _fetch(self, collection: str, doc_id: str) -> Any | None:
        """Busca o documento bruto pelo id, ou None se o Appwrite responder 404."""
        self._ensure(collection)
        try:
            return self._ler(lambda: self._db.get_document(self._database_id, collection, doc_id))
        except AppwriteException as exc:
            if exc.code == 404:
                return None
            raise

    def get_any(self, collection: str, doc_id: str) -> Doc | None:
        """Devolve o documento pelo id sem checar a família."""
        found = self._fetch(collection, doc_id)
        return _doc(found) if found else None

    def get(self, collection: str, family_id: str, doc_id: str) -> Doc | None:
        """Devolve o documento só se ele for da família pedida."""
        found = self._fetch(collection, doc_id)
        return _doc(found) if found and found.data.get("familyId") == family_id else None

    def list(self, collection: str, family_id: str, filters: dict[str, Any] | None = None) -> list[Doc]:
        """Busca todos os documentos da família, página por página, em ordem de criação.
        Os filtros são aplicados depois, em Python, e não na consulta ao Appwrite.
        """
        self._ensure(collection)
        out: list[Doc] = []
        offset = 0
        while True:
            queries: list[str] = [
                Query.equal("familyId", [family_id]),
                Query.order_asc("$createdAt"),
                Query.limit(PAGE),
                Query.offset(offset),
            ]
            page = self._ler(partial(self._db.list_documents, self._database_id, collection, queries))
            out.extend(_doc(d) for d in page.documents)
            if len(page.documents) < PAGE:
                break
            offset += PAGE
        for key, value in (filters or {}).items():
            out = [d for d in out if d.get(key) == value]
        return out

    def update(self, collection: str, family_id: str, doc_id: str, patch: Doc) -> Doc | None:
        """Atualiza o documento depois de confirmar que ele pertence à família."""
        if self.get(collection, family_id, doc_id) is None:
            return None
        return _doc(self._db.update_document(self._database_id, collection, doc_id, _clean(patch)))

    def delete(self, collection: str, family_id: str, doc_id: str) -> bool:
        """Apaga o documento depois de confirmar que ele pertence à família."""
        if self.get(collection, family_id, doc_id) is None:
            return False
        self._db.delete_document(self._database_id, collection, doc_id)
        return True
