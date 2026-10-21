"""Escolha do banco e do sistema de contas.

Este arquivo lê a configuração REPOSITORY_BACKEND e monta o par certo: repositório de dados e provedor de login.
Com "appwrite", usa o Appwrite para os dois; caso contrário, usa as versões em memória, boas para testes e
desenvolvimento.
Quem usa: main.py, ao criar a aplicação.
"""

from app.auth_provider import AppwriteAuthProvider, AuthProvider, MemoryAuthProvider
from app.core.config import Settings
from app.repositories.base import Repository
from app.repositories.memory import InMemoryRepository


def build_backends(settings: Settings) -> tuple[Repository, AuthProvider]:
    """Cria o repositório e o provedor de autenticação de acordo com as configurações."""
    if settings.repository_backend == "appwrite":
        from app.repositories.appwrite import AppwriteRepository

        return AppwriteRepository.from_settings(settings), AppwriteAuthProvider.from_settings(settings)
    return InMemoryRepository(), MemoryAuthProvider()
