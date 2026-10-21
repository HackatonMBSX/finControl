"""Guarda segredos com segurança.

Este arquivo cifra e decifra a chave de API do Asaas antes de ela ir para o banco. A cifra usa uma chave derivada do
JWT_SECRET, então só quem tem esse segredo consegue ler o valor de volta.
Quem usa: api/integracoes.py.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(secret: str) -> Fernet:
    """Monta o cifrador a partir do segredo da aplicação."""
    key = hashlib.sha256(f"fincontrol:segredos:{secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(secret: str, plain: str) -> str:
    """Cifra o texto e devolve um token que pode ser salvo no banco."""
    return _fernet(secret).encrypt(plain.encode()).decode()


def decrypt(secret: str, token: str) -> str | None:
    """Devolve o texto original, ou None se o token foi adulterado ou o segredo é outro."""
    try:
        return _fernet(secret).decrypt(token.encode()).decode()
    except InvalidToken:
        return None
