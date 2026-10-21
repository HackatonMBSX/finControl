"""Testes do repositório do Appwrite.

Este arquivo roda os testes de contrato contra o AppwriteRepository usando o banco falso de tests/fakes.py.
Também garante que o banco e as coleções são criados uma vez só e com índice, que o ping não deixa lixo, que
campos reservados são descartados e que erros 5xx passageiros são tentados de novo.
Se as variáveis APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID e APPWRITE_API_KEY existirem, o contrato roda também contra
um Appwrite de verdade, no banco fincontrol_test.
"""

import os

import pytest
from appwrite.exception import AppwriteException

from app.core.config import Settings
from app.repositories.appwrite import AppwriteRepository
from tests.contract.repository_contract import RepositoryContract
from tests.fakes import FakeDocumentsDB


class TestAppwriteRepositoryWithFake(RepositoryContract):
    """Roda o contrato e testes extras contra o Appwrite falso."""

    @pytest.fixture
    def repo(self) -> AppwriteRepository:
        """Entrega um repositório ligado a um Appwrite falso vazio."""
        return AppwriteRepository(FakeDocumentsDB())  # type: ignore[arg-type]

    def test_database_and_collection_created_once_and_indexed(self) -> None:
        """Verifica que banco e coleção são criados uma única vez e que a coleção ganha o índice por família."""
        fake = FakeDocumentsDB()
        r = AppwriteRepository(fake)  # type: ignore[arg-type]
        r.create("despesas", "f", {"a": 1})
        r.create("despesas", "f", {"a": 2})
        assert fake.databases == {"fincontrol"} and ("fincontrol", "despesas") in fake.collections
        assert fake.indexes == ["idx_family"]

    def test_ping_roundtrip_leaves_no_residue(self) -> None:
        """Verifica que o ping responde e não deixa documento sobrando na coleção healthcheck."""
        fake = FakeDocumentsDB()
        assert AppwriteRepository(fake).ping()  # type: ignore[arg-type]
        assert fake.collections[("fincontrol", "healthcheck")] == {}

    def test_reserved_keys_in_payload_are_dropped(self) -> None:
        """Verifica que campos com $ enviados pelo cliente são descartados e não trocam o id."""
        r = AppwriteRepository(FakeDocumentsDB())  # type: ignore[arg-type]
        doc = r.create("x", "f", {"$id": "hack", "valor": 1})
        assert doc["id"] != "hack" and "$id" not in doc


_LIVE = all(os.getenv(k) for k in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"))


@pytest.mark.skipif(not _LIVE, reason="defina APPWRITE_ENDPOINT/PROJECT_ID/API_KEY para rodar contra um Appwrite real")
class TestAppwriteRepositoryLive(RepositoryContract):
    """Roda o contrato contra um Appwrite real, só quando as credenciais existem."""

    @pytest.fixture
    def repo(self) -> AppwriteRepository:
        """Entrega um repositório ligado ao Appwrite real, no banco de testes."""
        s = Settings(
            repository_backend="appwrite",
            appwrite_endpoint=os.environ["APPWRITE_ENDPOINT"],
            appwrite_project_id=os.environ["APPWRITE_PROJECT_ID"],
            appwrite_api_key=os.environ["APPWRITE_API_KEY"],
            appwrite_database_id="fincontrol_test",
        )
        return AppwriteRepository.from_settings(s)


class _MongoLento(FakeDocumentsDB):
    """Appwrite falso que responde 500 na primeira tentativa de criar o banco."""

    def create(self, database_id: str, name: str, **kw: object) -> None:
        """Cria o banco e, só na primeira vez, finge uma falha 500."""
        super().create(database_id, name)
        if not getattr(self, "_falhou", False):
            self._falhou = True
            raise AppwriteException("Server Error", 500)


def test_erro_500_na_criacao_do_banco_e_tentado_de_novo() -> None:
    """Verifica que um erro 500 passageiro ao criar o banco é repetido e a gravação dá certo."""
    r = AppwriteRepository(_MongoLento(), retry_delay=0)  # type: ignore[arg-type]
    assert r.create("despesas", "f", {"a": 1})["a"] == 1


def test_erro_persistente_continua_sendo_erro() -> None:
    """Verifica que, se o erro 500 não passa, ele chega a quem chamou depois das tentativas."""

    class Quebrado(FakeDocumentsDB):
        """Appwrite falso que sempre responde 500 ao criar o banco."""

        def create(self, database_id: str, name: str, **kw: object) -> None:
            """Sempre falha com erro 500."""
            raise AppwriteException("Server Error", 500)

    with pytest.raises(AppwriteException):
        AppwriteRepository(Quebrado(), retry_delay=0).create("x", "f", {})  # type: ignore[arg-type]


def test_warm_up_cria_todas_as_colecoes() -> None:
    """Verifica que o warm_up cria as coleções principais do app."""
    fake = FakeDocumentsDB()
    AppwriteRepository(fake).warm_up()  # type: ignore[arg-type]
    assert {c for (_, c) in fake.collections} >= {"familias", "perfis", "despesas", "configuracoes", "integracoes"}


def test_leitura_com_erro_500_passageiro_e_tentada_de_novo() -> None:
    """Verifica que uma leitura com erro 500 passageiro é repetida e devolve o documento."""

    class Instavel(FakeDocumentsDB):
        """Appwrite falso que falha nas leituras enquanto houver falhas programadas."""

        falhas = 0

        def get_document(self, db: str, col: str, did: str):  # type: ignore[no-untyped-def]
            """Responde 500 enquanto restarem falhas programadas; depois lê normalmente."""
            if self.falhas:
                self.falhas -= 1
                raise AppwriteException("Server Error", 500)
            return super().get_document(db, col, did)

    fake = Instavel()
    r = AppwriteRepository(fake, retry_delay=0)  # type: ignore[arg-type]
    criado = r.create("x", "f", {"a": 1})
    fake.falhas = 1
    assert r.get("x", "f", criado["id"]) is not None
