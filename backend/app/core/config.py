"""Configurações da aplicação.

Este arquivo reúne todas as opções do backend: nome e versão da API, origens liberadas no CORS, qual banco usar
(memória ou Appwrite), dados de acesso ao Appwrite, segredo do JWT e se o cadastro está aberto.
Os valores vêm de variáveis de ambiente ou do arquivo .env; o que não for informado usa o padrão daqui.
Em produção, a aplicação se recusa a subir com um JWT_SECRET fraco ou de desenvolvimento.
Quem usa: main.py, auth_provider.py, repositories/factory.py e repositories/appwrite.py.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Opções do backend lidas das variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FinControl API"
    app_version: str = "1.0.0"
    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8080"])
    enable_docs: bool = True

    repository_backend: Literal["memory", "appwrite"] = "memory"
    appwrite_endpoint: str = "http://appwrite/v1"
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""
    appwrite_database_id: str = "fincontrol"

    jwt_secret: str = "dev-only-change-me-dev-only-change-me-0123"  # noqa: S105
    jwt_expire_minutes: int = 480
    allow_registration: bool = True

    @model_validator(mode="after")
    def _production_requires_real_secret(self) -> "Settings":
        """Impede subir em produção com o segredo de desenvolvimento ou com menos de 32 caracteres."""
        if self.app_env == "production" and (self.jwt_secret.startswith("dev-only") or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET precisa ter 32+ caracteres e não pode ser o valor de desenvolvimento")
        return self


@lru_cache
def get_settings() -> Settings:
    """Devolve as configurações, lidas uma única vez e reaproveitadas nas chamadas seguintes."""
    return Settings()
