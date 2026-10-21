"""Testes das rotas de infraestrutura e do comportamento geral do app.

Este arquivo garante que /health, /ready, /version e a raiz respondem certo, que o /ready acusa banco fora do ar,
que erros seguem o formato padrão sem vazar detalhes internos, que o Swagger pode ser ligado ou desligado e que
produção recusa um JWT_SECRET fraco.
"""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.memory import InMemoryRepository


def test_health(client: TestClient) -> None:
    """Verifica que /health responde ok e já traz o id da requisição e o cabeçalho de segurança."""
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-request-id"] and r.headers["x-content-type-options"] == "nosniff"


def test_ready_ok(client: TestClient) -> None:
    """Verifica que /ready responde ready quando o banco está de pé."""
    assert client.get("/ready").json() == {"status": "ready"}


def test_ready_unavailable_when_repository_fails(settings: Settings) -> None:
    """Verifica que /ready responde 503 quando o banco falha."""

    class Broken(InMemoryRepository):
        """Repositório que simula banco fora do ar."""

        def ping(self) -> bool:
            """Sempre falha com erro de conexão."""
            raise ConnectionError("db down")

    c = TestClient(create_app(settings, Broken()))
    r = c.get("/ready")
    assert r.status_code == 503 and r.json() == {"status": "unavailable"}


def test_version(client: TestClient) -> None:
    """Verifica que /version informa o ambiente em que o app está rodando."""
    assert client.get("/version").json()["env"] == "test"


def test_unknown_route_uses_standard_error_envelope(client: TestClient) -> None:
    """Verifica que uma rota inexistente devolve 404 no formato padrão de erro, com requestId."""
    r = client.get("/nao-existe")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "http_404" and err["requestId"]


def test_unhandled_error_does_not_leak_details(settings: Settings, repo: InMemoryRepository) -> None:
    """Verifica que um erro inesperado vira 500 genérico sem mostrar a mensagem interna."""
    app = create_app(settings, repo)

    @app.get("/boom")
    def boom() -> None:
        """Rota de teste que sempre lança um erro inesperado."""
        raise RuntimeError("segredo interno")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500 and "segredo" not in r.text
    assert r.json()["error"]["code"] == "internal_error"


def test_docs_enabled_by_default_even_in_production(repo: InMemoryRepository) -> None:
    """Verifica que o Swagger fica ligado por padrão, mesmo em produção."""
    c = TestClient(create_app(Settings(app_env="production", jwt_secret="x" * 40), repo))
    assert c.get("/docs").status_code == 200 and c.get("/openapi.json").status_code == 200


def test_docs_can_be_disabled(repo: InMemoryRepository) -> None:
    """Verifica que o Swagger e o openapi.json somem quando a opção é desligada."""
    c = TestClient(create_app(Settings(app_env="production", jwt_secret="x" * 40, enable_docs=False), repo))
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


def test_root_opens_docs_or_describes_service(settings: Settings, repo: InMemoryRepository) -> None:
    """Verifica que a raiz redireciona ao Swagger, ou mostra nome e versão quando ele está desligado."""
    r = TestClient(create_app(settings, repo)).get("/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/docs"
    off = TestClient(create_app(Settings(app_env="test", enable_docs=False), repo)).get("/")
    assert off.status_code == 200 and off.json()["name"] == "FinControl API"


def test_production_rejects_weak_jwt_secret() -> None:
    """Verifica que produção não sobe com o JWT_SECRET de desenvolvimento."""
    import pytest

    with pytest.raises(ValueError):
        Settings(app_env="production")
