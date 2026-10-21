"""Testes de contrato que todo repositório precisa passar.

Este arquivo reúne, numa classe base, os comportamentos esperados de qualquer repositório: criar e ler,
isolar famílias, filtrar, proteger id e família na atualização, apagar, devolver cópias e listar muitos itens.
Cada implementação herda a classe e só troca a fixture repo, garantindo que memória e Appwrite se comportam igual.
Quem usa: tests/contract/test_memory_repository.py e tests/contract/test_appwrite_repository.py.
"""

import pytest

from app.repositories.base import Repository


class RepositoryContract:
    """Conjunto de testes que vale para qualquer implementação de repositório."""

    @pytest.fixture
    def repo(self) -> Repository:
        """Deve ser sobrescrita por cada implementação para entregar o repositório testado."""
        raise NotImplementedError

    def test_create_and_get(self, repo: Repository) -> None:
        """Verifica que o documento criado ganha id, família e data, e pode ser lido."""
        doc = repo.create("despesas", "fam1", {"descricao": "Luz", "valor": 100})
        assert doc["id"] and doc["familyId"] == "fam1" and doc["createdAt"]
        assert repo.get("despesas", "fam1", doc["id"])["descricao"] == "Luz"

    def test_isolation_between_families(self, repo: Repository) -> None:
        """Verifica que outra família não consegue ler, listar, alterar nem apagar o documento."""
        doc = repo.create("despesas", "fam1", {"descricao": "Luz"})
        assert repo.get("despesas", "fam2", doc["id"]) is None
        assert repo.list("despesas", "fam2") == []
        assert repo.update("despesas", "fam2", doc["id"], {"descricao": "x"}) is None
        assert repo.delete("despesas", "fam2", doc["id"]) is False
        assert repo.get("despesas", "fam1", doc["id"]) is not None

    def test_list_with_filters(self, repo: Repository) -> None:
        """Verifica que a listagem aplica filtros de igualdade."""
        repo.create("despesas", "fam1", {"status": "PAGO"})
        repo.create("despesas", "fam1", {"status": "ABERTO"})
        assert len(repo.list("despesas", "fam1")) == 2
        assert len(repo.list("despesas", "fam1", {"status": "PAGO"})) == 1

    def test_update_merges_and_protects_identity(self, repo: Repository) -> None:
        """Verifica que a atualização junta campos e ignora tentativas de trocar id e família."""
        doc = repo.create("despesas", "fam1", {"valor": 10, "status": "ABERTO"})
        out = repo.update("despesas", "fam1", doc["id"], {"status": "PAGO", "familyId": "hack", "id": "outro"})
        assert out is not None and out["status"] == "PAGO" and out["valor"] == 10
        assert out["familyId"] == "fam1" and out["id"] == doc["id"]

    def test_delete(self, repo: Repository) -> None:
        """Verifica que apagar funciona uma vez e devolve False na segunda."""
        doc = repo.create("despesas", "fam1", {"valor": 1})
        assert repo.delete("despesas", "fam1", doc["id"]) is True
        assert repo.get("despesas", "fam1", doc["id"]) is None
        assert repo.delete("despesas", "fam1", doc["id"]) is False

    def test_returns_copies(self, repo: Repository) -> None:
        """Verifica que mexer no documento devolvido não altera o que está guardado."""
        doc = repo.create("despesas", "fam1", {"tags": ["a"]})
        doc["tags"].append("b")
        assert repo.get("despesas", "fam1", doc["id"])["tags"] == ["a"]

    def test_get_any_ignores_family(self, repo: Repository) -> None:
        """Verifica que get_any acha o documento sem saber a família e devolve None se ele não existe."""
        doc = repo.create("perfis", "fam1", {"nome": "A"}, doc_id="u1")
        assert repo.get_any("perfis", "u1")["familyId"] == "fam1" and doc["id"] == "u1"
        assert repo.get_any("perfis", "nao-existe") is None

    def test_many_documents_are_all_listed(self, repo: Repository) -> None:
        """Verifica que a listagem traz todos os documentos mesmo passando do tamanho de uma página."""
        for i in range(130):
            repo.create("despesas", "fam1", {"n": i})
        assert len(repo.list("despesas", "fam1")) == 130
