"""Imitação do banco do Appwrite para os testes.

Este arquivo simula, em memória, as chamadas do Appwrite usadas por repositories/appwrite.py: criar banco,
coleção e índice, e criar, ler, atualizar, apagar e listar documentos com paginação.
Ele imita também os erros do Appwrite (400 para id inválido, 404 e 409), para testar o repositório sem rede.
Quem usa: tests/contract/test_appwrite_repository.py.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from appwrite.exception import AppwriteException
from appwrite.models.document import Document
from appwrite.models.document_list import DocumentList


def _raw(db: str, col: str, did: str, data: dict[str, Any], created: str, updated: str) -> dict[str, Any]:
    """Monta o documento no formato bruto do Appwrite, com os campos que começam com $."""
    return {
        "$id": did, "$sequence": "1", "$collectionId": col, "$databaseId": db,
        "$createdAt": created, "$updatedAt": updated, "$permissions": [], **data,
    }  # fmt: skip


class FakeDocumentsDB:
    """Banco do Appwrite de mentira, guardado em dicionários."""

    def __init__(self) -> None:
        """Começa sem bancos, coleções nem índices, e com o relógio zerado."""
        self.databases: set[str] = set()
        self.collections: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        self.indexes: list[str] = []
        self._clock = 0

    def _tick(self) -> str:
        """Avança o relógio falso e devolve uma data sempre maior, para a ordem de criação ser estável."""
        self._clock += 1
        return datetime(2026, 10, 20, 12, 0, tzinfo=UTC).replace(microsecond=self._clock).isoformat()

    @staticmethod
    def _valid_id(value: str) -> None:
        """Recusa com erro 400 ids que o Appwrite não aceitaria."""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}", value):
            raise AppwriteException(f"Invalid id: {value}", 400)

    def create(self, database_id: str, name: str, **_: Any) -> None:
        """Cria o banco; responde 409 se ele já existir."""
        self._valid_id(database_id)
        if database_id in self.databases:
            raise AppwriteException("exists", 409)
        self.databases.add(database_id)

    def create_collection(self, database_id: str, collection_id: str, name: str, **_: Any) -> None:
        """Cria a coleção; responde 409 se ela já existir."""
        self._valid_id(collection_id)
        if (database_id, collection_id) in self.collections:
            raise AppwriteException("exists", 409)
        self.collections[(database_id, collection_id)] = {}

    def create_index(self, database_id: str, collection_id: str, key: str, type: str, attributes: list[str]) -> None:
        """Anota o nome do índice criado, para os testes conferirem."""
        self.indexes.append(key)

    def _col(self, db: str, col: str) -> dict[str, dict[str, Any]]:
        """Devolve os documentos da coleção, ou responde 404 se ela não existir."""
        if (db, col) not in self.collections:
            raise AppwriteException("collection not found", 404)
        return self.collections[(db, col)]

    def create_document(self, db: str, col: str, did: str, data: dict[str, Any]) -> Document[Any]:
        """Grava uma cópia do documento com datas; responde 409 se o id já existir."""
        bucket = self._col(db, col)
        self._valid_id(did)
        if did in bucket:
            raise AppwriteException("exists", 409)
        now = self._tick()
        bucket[did] = {"data": json.loads(json.dumps(data)), "created": now, "updated": now}
        return self.get_document(db, col, did)

    def get_document(self, db: str, col: str, did: str) -> Document[Any]:
        """Devolve uma cópia do documento no formato do Appwrite, ou responde 404."""
        row = self._col(db, col).get(did)
        if row is None:
            raise AppwriteException("not found", 404)
        return Document.with_data(
            _raw(db, col, did, json.loads(json.dumps(row["data"])), row["created"], row["updated"])
        )

    def update_document(self, db: str, col: str, did: str, data: dict[str, Any]) -> Document[Any]:
        """Junta as mudanças ao documento e renova a data de atualização."""
        row = self._col(db, col).get(did)
        if row is None:
            raise AppwriteException("not found", 404)
        row["data"].update(json.loads(json.dumps(data)))
        row["updated"] = self._tick()
        return self.get_document(db, col, did)

    def delete_document(self, db: str, col: str, did: str) -> None:
        """Apaga o documento, sem erro se ele não existir."""
        self._col(db, col).pop(did, None)

    def list_documents(self, db: str, col: str, queries: list[str]) -> DocumentList[Any]:
        """Lista documentos aplicando os filtros equal, limit e offset, em ordem de criação.
        O limite padrão é 25, como no Appwrite.
        """
        rows = [(did, r) for did, r in self._col(db, col).items()]
        limit, offset = 25, 0
        for q in map(json.loads, queries):
            if q["method"] == "equal":
                rows = [(d, r) for d, r in rows if r["data"].get(q["attribute"]) in q["values"]]
            elif q["method"] == "limit":
                limit = q["values"][0]
            elif q["method"] == "offset":
                offset = q["values"][0]
        rows.sort(key=lambda x: x[1]["created"])
        page = rows[offset : offset + limit]
        docs = [_raw(db, col, d, json.loads(json.dumps(r["data"])), r["created"], r["updated"]) for d, r in page]
        return DocumentList.with_data({"total": len(rows), "documents": docs})


def new_id() -> str:
    """Gera um id aleatório de 20 caracteres."""
    return uuid.uuid4().hex[:20]
