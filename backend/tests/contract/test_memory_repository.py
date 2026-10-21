"""Testes do repositório em memória.

Este arquivo roda os testes de contrato de repository_contract.py contra o InMemoryRepository e garante que ele
recusa criar dois documentos com o mesmo id.
"""

import pytest

from app.repositories.memory import InMemoryRepository
from tests.contract.repository_contract import RepositoryContract


class TestInMemoryRepository(RepositoryContract):
    """Roda o contrato de repositório contra a versão em memória."""

    @pytest.fixture
    def repo(self) -> InMemoryRepository:
        """Entrega um repositório em memória vazio."""
        return InMemoryRepository()

    def test_duplicate_id_rejected(self, repo: InMemoryRepository) -> None:
        """Verifica que criar de novo com o mesmo id lança ValueError."""
        repo.create("x", "f", {}, doc_id="a")
        with pytest.raises(ValueError):
            repo.create("x", "f", {}, doc_id="a")
