"""Repositório que guarda os dados só na memória.

Este arquivo implementa o contrato de repositories/base.py usando dicionários Python, sem banco de verdade.
Tudo some quando o processo reinicia, por isso ele serve para desenvolvimento local e para os testes.
Os documentos são sempre copiados na entrada e na saída, para que quem chama não altere o dado guardado sem querer.
Quem usa: repositories/factory.py (quando REPOSITORY_BACKEND=memory) e os testes.
"""

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from app.repositories.base import Doc, Repository


def _now() -> str:
    """Devolve a data e hora atual em UTC no formato ISO, usada em createdAt e updatedAt."""
    return datetime.now(UTC).isoformat()


class InMemoryRepository(Repository):
    """Repositório em memória, organizado por coleção e por id do documento."""

    def __init__(self) -> None:
        """Começa sem nenhuma coleção."""
        self._data: dict[str, dict[str, Doc]] = {}

    def ping(self) -> bool:
        """Sempre responde True, pois não há banco externo para checar."""
        return True

    def create(self, collection: str, family_id: str, data: Doc, doc_id: str | None = None) -> Doc:
        """Guarda uma cópia do documento com id, família e datas; recusa id repetido."""
        did = doc_id or uuid.uuid4().hex[:20]
        bucket = self._data.setdefault(collection, {})
        if did in bucket:
            raise ValueError(f"documento {did} já existe em {collection}")
        now = _now()
        doc = {**copy.deepcopy(data), "id": did, "familyId": family_id, "createdAt": now, "updatedAt": now}
        bucket[did] = doc
        return copy.deepcopy(doc)

    def get(self, collection: str, family_id: str, doc_id: str) -> Doc | None:
        """Devolve uma cópia do documento se ele existir e for da família."""
        doc = self._data.get(collection, {}).get(doc_id)
        return copy.deepcopy(doc) if doc and doc["familyId"] == family_id else None

    def list(self, collection: str, family_id: str, filters: dict[str, Any] | None = None) -> list[Doc]:
        """Devolve cópias dos documentos da família que batem com os filtros, em ordem de criação."""
        docs = [d for d in self._data.get(collection, {}).values() if d["familyId"] == family_id]
        for key, value in (filters or {}).items():
            docs = [d for d in docs if d.get(key) == value]
        return [copy.deepcopy(d) for d in sorted(docs, key=lambda d: d["createdAt"])]

    def get_any(self, collection: str, doc_id: str) -> Doc | None:
        """Devolve uma cópia do documento sem checar a família."""
        doc = self._data.get(collection, {}).get(doc_id)
        return copy.deepcopy(doc) if doc else None

    def update(self, collection: str, family_id: str, doc_id: str, patch: Doc) -> Doc | None:
        """Aplica as mudanças sem mexer em id, família e data de criação, e renova o updatedAt."""
        doc = self._data.get(collection, {}).get(doc_id)
        if not doc or doc["familyId"] != family_id:
            return None
        protected = {"id", "familyId", "createdAt"}
        doc.update({k: copy.deepcopy(v) for k, v in patch.items() if k not in protected})
        doc["updatedAt"] = _now()
        return copy.deepcopy(doc)

    def delete(self, collection: str, family_id: str, doc_id: str) -> bool:
        """Remove o documento se ele for da família."""
        doc = self._data.get(collection, {}).get(doc_id)
        if not doc or doc["familyId"] != family_id:
            return False
        del self._data[collection][doc_id]
        return True
