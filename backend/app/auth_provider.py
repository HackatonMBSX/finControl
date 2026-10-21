"""Provedores de autenticação: criar contas e conferir senhas.

Um provedor de autenticação é quem guarda as contas de usuário e diz se o e-mail e a senha estão corretos.
Este arquivo define o contrato comum e duas versões: uma em memória (para testes e desenvolvimento) e uma que usa
o serviço de contas do Appwrite (para produção).
O provedor só cuida da identidade; os dados do perfil e da família ficam no repositório.
Quem usa: api/auth.py, api/conta.py, api/deps.py e repositories/factory.py.
"""

import contextlib
import uuid
from abc import ABC, abstractmethod

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.id import ID
from appwrite.services.account import Account
from appwrite.services.users import Users

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_password, verify_password


class EmailInUseError(Exception):
    """Erro lançado quando já existe uma conta com o e-mail informado."""


class AuthProvider(ABC):
    """Interface que todo provedor de autenticação precisa seguir."""

    @abstractmethod
    def create_user(self, email: str, password: str, name: str) -> str:
        """Cria a conta e devolve o id do usuário; lança EmailInUseError se o e-mail já existir."""

    @abstractmethod
    def verify(self, email: str, password: str) -> str | None:
        """Confere e-mail e senha e devolve o id do usuário, ou None se não baterem."""

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Apaga a conta do usuário."""


class MemoryAuthProvider(AuthProvider):
    """Provedor que guarda as contas em memória, com a senha em hash."""

    def __init__(self) -> None:
        """Começa sem nenhuma conta; cada e-mail aponta para o id e o hash da senha."""
        self._users: dict[str, tuple[str, str]] = {}

    def create_user(self, email: str, password: str, name: str) -> str:
        """Cria a conta em memória guardando só o hash da senha; o nome não é armazenado."""
        if email in self._users:
            raise EmailInUseError
        uid = uuid.uuid4().hex[:20]
        self._users[email] = (uid, hash_password(password))
        return uid

    def verify(self, email: str, password: str) -> str | None:
        """Devolve o id do usuário se o e-mail existir e a senha bater com o hash."""
        found = self._users.get(email)
        return found[0] if found and verify_password(password, found[1]) else None

    def delete_user(self, user_id: str) -> None:
        """Remove as contas que têm o id informado."""
        self._users = {e: v for e, v in self._users.items() if v[0] != user_id}


class AppwriteAuthProvider(AuthProvider):
    """Provedor que usa o serviço de contas do Appwrite."""

    def __init__(self, endpoint: str, project_id: str, api_key: str) -> None:
        """Monta dois clientes: um administrador, com chave de API, e um público, que entra como usuário comum."""
        self._admin = Client().set_endpoint(endpoint).set_project(project_id).set_key(api_key)
        self._public = Client().set_endpoint(endpoint).set_project(project_id)

    @classmethod
    def from_settings(cls, s: Settings) -> "AppwriteAuthProvider":
        """Cria o provedor com endereço, projeto e chave de API vindos das configurações."""
        return cls(s.appwrite_endpoint, s.appwrite_project_id, s.appwrite_api_key)

    def create_user(self, email: str, password: str, name: str) -> str:
        """Cria o usuário no Appwrite; um 409 vira EmailInUseError."""
        try:
            return str(Users(self._admin).create(ID.unique(), email=email, password=password, name=name).id)
        except AppwriteException as exc:
            if exc.code == 409:
                raise EmailInUseError from exc
            raise

    def verify(self, email: str, password: str) -> str | None:
        """Confere a senha abrindo uma sessão no Appwrite e apagando-a em seguida, pois o login real usa o JWT do app.
        Responde None para credenciais erradas e lança erro 429 quando há tentativas demais.
        """
        try:
            session = Account(self._public).create_email_password_session(email, password)
        except AppwriteException as exc:
            if exc.code in (400, 401):
                return None
            if exc.code == 429:
                raise AppError(429, "too_many_attempts", "Muitas tentativas. Aguarde alguns minutos.") from exc
            raise
        with contextlib.suppress(AppwriteException):
            Users(self._admin).delete_session(session.userid, session.id)
        return str(session.userid)

    def delete_user(self, user_id: str) -> None:
        """Apaga o usuário no Appwrite, ignorando erros como conta já apagada."""
        with contextlib.suppress(AppwriteException):
            Users(self._admin).delete(user_id)
