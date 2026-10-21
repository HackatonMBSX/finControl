"""Peças compartilhadas pelos testes.

Este arquivo cria, para cada teste, configurações de teste, um repositório em memória novo e um cliente HTTP que
conversa com a API sem subir servidor. Assim cada teste começa do zero, sem banco de verdade.
Fixtures são funções que o pytest roda antes do teste para entregar esses objetos prontos.
Quem usa: todos os arquivos de teste, de forma automática.
"""

import pytest
from fastapi.testclient import TestClient

from app.auth_provider import MemoryAuthProvider
from app.core.config import Settings
from app.main import create_app
from app.repositories.memory import InMemoryRepository


@pytest.fixture
def settings() -> Settings:
    """Entrega configurações de teste com o banco em memória."""
    return Settings(app_env="test", repository_backend="memory", cors_origins=["http://localhost:8080"])


@pytest.fixture
def repo() -> InMemoryRepository:
    """Entrega um repositório em memória vazio."""
    return InMemoryRepository()


@pytest.fixture
def client(settings: Settings, repo: InMemoryRepository) -> TestClient:
    """Entrega um cliente HTTP da API que devolve erros 500 como resposta em vez de quebrar o teste."""
    return TestClient(create_app(settings, repo, MemoryAuthProvider()), raise_server_exceptions=False)
