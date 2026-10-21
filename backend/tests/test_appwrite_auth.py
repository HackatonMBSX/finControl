"""Testes do provedor de autenticação do Appwrite.

Este arquivo troca as classes Users e Account do Appwrite por imitações simples e garante que o provedor cria
usuários, converte e-mail repetido em EmailInUseError, apaga a sessão aberta só para conferir a senha, devolve
None para credenciais erradas, transforma excesso de tentativas em erro 429 e apaga usuários sem quebrar.
"""

from types import SimpleNamespace

import pytest
from appwrite.exception import AppwriteException

from app import auth_provider as mod
from app.core.errors import AppError


class FakeUsers:
    """Imitação do serviço Users do Appwrite que anota as chamadas recebidas."""

    created: list[dict] = []
    deleted_sessions: list[tuple[str, str]] = []
    deleted_users: list[str] = []
    fail_with: int | None = None

    def __init__(self, client: object) -> None:
        """Aceita o cliente e não faz nada com ele."""

    def create(self, user_id: str, email: str, password: str, name: str) -> SimpleNamespace:
        """Anota o usuário criado, ou falha com o código configurado em fail_with."""
        if FakeUsers.fail_with:
            raise AppwriteException("x", FakeUsers.fail_with)
        FakeUsers.created.append({"email": email, "name": name})
        return SimpleNamespace(id="u123")

    def delete_session(self, user_id: str, session_id: str) -> None:
        """Anota a sessão apagada."""
        FakeUsers.deleted_sessions.append((user_id, session_id))

    def delete(self, user_id: str) -> None:
        """Anota o usuário apagado."""
        FakeUsers.deleted_users.append(user_id)


class FakeAccount:
    """Imitação do serviço Account do Appwrite usado para conferir a senha."""

    code: int | None = None

    def __init__(self, client: object) -> None:
        """Aceita o cliente e não faz nada com ele."""

    def create_email_password_session(self, email: str, password: str) -> SimpleNamespace:
        """Devolve uma sessão falsa, ou falha com o código configurado."""
        if FakeAccount.code:
            raise AppwriteException("x", FakeAccount.code)
        return SimpleNamespace(userid="u123", id="s1")


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> mod.AppwriteAuthProvider:
    """Entrega um provedor do Appwrite usando as imitações, com as anotações zeradas."""
    monkeypatch.setattr(mod, "Users", FakeUsers)
    monkeypatch.setattr(mod, "Account", FakeAccount)
    FakeUsers.created, FakeUsers.deleted_sessions, FakeUsers.deleted_users = [], [], []
    FakeUsers.fail_with = FakeAccount.code = None
    return mod.AppwriteAuthProvider("http://appwrite/v1", "proj", "key")


def test_create_user(provider: mod.AppwriteAuthProvider) -> None:
    """Verifica que criar usuário devolve o id e envia e-mail e nome ao Appwrite."""
    assert provider.create_user("a@x.com", "senha-forte-1", "Ana") == "u123"
    assert FakeUsers.created == [{"email": "a@x.com", "name": "Ana"}]


def test_create_user_conflict_maps_to_email_in_use(provider: mod.AppwriteAuthProvider) -> None:
    """Verifica que um 409 do Appwrite vira EmailInUseError."""
    FakeUsers.fail_with = 409
    with pytest.raises(mod.EmailInUseError):
        provider.create_user("a@x.com", "senha-forte-1", "Ana")


def test_verify_ok_removes_the_validation_session(provider: mod.AppwriteAuthProvider) -> None:
    """Verifica que a senha certa devolve o id e a sessão de conferência é apagada."""
    assert provider.verify("a@x.com", "pw") == "u123"
    assert FakeUsers.deleted_sessions == [("u123", "s1")]


@pytest.mark.parametrize("code", [400, 401])
def test_verify_wrong_credentials_returns_none(provider: mod.AppwriteAuthProvider, code: int) -> None:
    """Verifica que respostas 400 e 401 do Appwrite viram None."""
    FakeAccount.code = code
    assert provider.verify("a@x.com", "pw") is None


def test_verify_rate_limited_and_unexpected_errors(provider: mod.AppwriteAuthProvider) -> None:
    """Verifica que 429 vira AppError com status 429 e que outros erros seguem adiante."""
    FakeAccount.code = 429
    with pytest.raises(AppError) as e:
        provider.verify("a@x.com", "pw")
    assert e.value.status == 429
    FakeAccount.code = 500
    with pytest.raises(AppwriteException):
        provider.verify("a@x.com", "pw")


def test_delete_user_is_best_effort(provider: mod.AppwriteAuthProvider) -> None:
    """Verifica que apagar o usuário chama o Appwrite com o id certo."""
    provider.delete_user("u123")
    assert FakeUsers.deleted_users == ["u123"]
