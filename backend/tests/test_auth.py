"""Testes de cadastro, login, tokens e papéis.

Este arquivo garante que o hash de senha funciona, que cadastro, login e /auth/me funcionam com e-mail sem
diferenciar maiúsculas, que e-mail repetido é recusado, que há limite de senhas erradas, que tokens ausentes,
inválidos ou expirados são barrados e que só o admin gerencia usuários, sempre dentro da própria família.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import auth as auth_module
from app.core.config import Settings
from app.core.security import create_token, hash_password, verify_password
from app.main import create_app
from app.repositories.memory import InMemoryRepository

REG = {"familia": "Família Silva", "nome": "Rafael", "email": "Rafael@Example.com", "senha": "senha-forte-1"}


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    """Zera o contador de senhas erradas antes de cada teste, para um teste não bloquear o outro."""
    auth_module._failures.clear()


def _register(client: TestClient, **over: str) -> dict:
    """Cadastra uma família pela API, com dados padrão que podem ser trocados, e devolve a resposta."""
    r = client.post("/api/v1/auth/register", json={**REG, **over})
    assert r.status_code == 201, r.text
    return r.json()


def _h(token: str) -> dict[str, str]:
    """Monta o cabeçalho Authorization com o token."""
    return {"Authorization": f"Bearer {token}"}


def test_password_hash_roundtrip() -> None:
    """Verifica que a senha certa bate com o hash, e a errada ou um hash inválido não."""
    h = hash_password("abc12345")
    assert h != "abc12345" and verify_password("abc12345", h) and not verify_password("outra", h)
    assert not verify_password("x", "lixo")


def test_register_login_me(client: TestClient) -> None:
    """Verifica que quem se cadastra vira admin, entra com o e-mail em outra caixa e vê seus dados sem a senha."""
    out = _register(client)
    assert out["user"]["papel"] == "admin" and out["user"]["email"] == "rafael@example.com"
    r = client.post("/api/v1/auth/login", json={"email": "RAFAEL@example.com", "senha": REG["senha"]})
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers=_h(r.json()["accessToken"]))
    assert me.status_code == 200 and me.json()["nome"] == "Rafael"
    assert "senhaHash" not in me.text


def test_duplicate_email_rejected(client: TestClient) -> None:
    """Verifica que cadastrar o mesmo e-mail de novo responde 409."""
    _register(client)
    r = client.post("/api/v1/auth/register", json=REG)
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_in_use"


def test_wrong_password_and_rate_limit(client: TestClient) -> None:
    """Verifica que, depois de 5 senhas erradas, até a senha certa é barrada com 429."""
    _register(client)
    for _ in range(5):
        r = client.post("/api/v1/auth/login", json={"email": REG["email"], "senha": "errada"})
        assert r.status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": REG["email"], "senha": REG["senha"]}).status_code == 429


def test_requires_token(client: TestClient) -> None:
    """Verifica que rotas protegidas recusam pedido sem token ou com token inválido."""
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=_h("lixo")).json()["error"]["code"] == "invalid_token"


def test_expired_token_rejected(client: TestClient, settings: Settings) -> None:
    """Verifica que um token expirado é recusado."""
    tok = create_token(settings.jwt_secret, -1, user_id="u", family_id="f", role="admin")
    assert client.get("/api/v1/auth/me", headers=_h(tok)).status_code == 401


def test_registration_can_be_disabled(repo: InMemoryRepository) -> None:
    """Verifica que o cadastro responde 403 quando está desligado."""
    app = create_app(Settings(app_env="test", allow_registration=False), repo)
    assert TestClient(app).post("/api/v1/auth/register", json=REG).status_code == 403


def test_rbac_only_admin_manages_users_and_families_are_isolated(client: TestClient) -> None:
    """Verifica que só o admin lista usuários e que cada família vê apenas os seus."""
    admin = _register(client)["accessToken"]
    r = client.post(
        "/api/v1/usuarios",
        headers=_h(admin),
        json={"nome": "Mariana", "email": "mari@example.com", "senha": "senha-forte-2", "papel": "leitor"},
    )
    assert r.status_code == 201
    leitor = client.post("/api/v1/auth/login", json={"email": "mari@example.com", "senha": "senha-forte-2"}).json()
    assert leitor["user"]["familyId"] == _register_family(client, admin)
    assert client.get("/api/v1/usuarios", headers=_h(leitor["accessToken"])).status_code == 403
    assert len(client.get("/api/v1/usuarios", headers=_h(admin)).json()) == 2
    other = _register(client, email="outra@example.com", familia="Outra")["accessToken"]
    assert len(client.get("/api/v1/usuarios", headers=_h(other)).json()) == 1


def _register_family(client: TestClient, token: str) -> str:
    """Devolve o id da família do usuário dono do token."""
    return client.get("/api/v1/auth/me", headers=_h(token)).json()["familyId"]
