"""Contrato comum dos repositórios de dados.

Um repositório é a camada que lê e grava documentos no banco, escondendo do resto do código qual banco é usado.
Este arquivo define as operações que todo repositório precisa oferecer (criar, buscar, listar, atualizar, apagar)
e o tipo Doc, que é um documento representado como dicionário.
Quase toda operação recebe o id da família, para que uma família nunca enxergue dados de outra.
Quem implementa: repositories/memory.py e repositories/appwrite.py. Quem usa: api/ e main.py.
"""

from abc import ABC, abstractmethod
from typing import Any

Doc = dict[str, Any]


class Repository(ABC):
    """Interface que todo repositório de dados precisa seguir."""

    @abstractmethod
    def ping(self) -> bool:
        """Confere se o banco está respondendo; devolve True quando está tudo certo."""

    @abstractmethod
    def create(self, collection: str, family_id: str, data: Doc, doc_id: str | None = None) -> Doc:
        """Grava um novo documento na coleção, ligado à família, e devolve o documento salvo.
        Usa o id informado ou gera um; lança ValueError se o id já existir.
        """

    @abstractmethod
    def get(self, collection: str, family_id: str, doc_id: str) -> Doc | None:
        """Devolve o documento pelo id, ou None se ele não existir ou for de outra família."""

    @abstractmethod
    def list(self, collection: str, family_id: str, filters: dict[str, Any] | None = None) -> list[Doc]:
        """Devolve os documentos da família na coleção, aplicando filtros simples de igualdade."""

    @abstractmethod
    def update(self, collection: str, family_id: str, doc_id: str, patch: Doc) -> Doc | None:
        """Aplica as mudanças ao documento da família e devolve o resultado, ou None se ele não for encontrado."""

    @abstractmethod
    def get_any(self, collection: str, doc_id: str) -> Doc | None:
        """Devolve o documento pelo id sem checar a família, ou None se ele não existir."""

    @abstractmethod
    def delete(self, collection: str, family_id: str, doc_id: str) -> bool:
        """Apaga o documento da família; devolve False se ele não for encontrado."""
