"""Senhas e tokens de acesso.

Este arquivo guarda senhas como hash scrypt (um cálculo de mão única, lento de propósito, que dificulta descobrir
a senha por tentativa) e confere a senha digitada contra esse hash.
Também cria e lê tokens JWT: um texto assinado que diz quem é o usuário, a família e o papel dele, e que expira.
Quem usa: auth_provider.py (senhas), api/auth.py (cria tokens) e api/deps.py (lê tokens).
"""

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    """Gera o hash scrypt da senha com sal aleatório, guardando os parâmetros junto para conferir depois."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    """Confere a senha contra o hash salvo; devolve False se não bater ou se o hash estiver malformado."""
    try:
        _, n, r, p, salt, digest = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(calc, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


def create_token(secret: str, minutes: int, *, user_id: str, family_id: str, role: str) -> str:
    """Cria um JWT assinado com o usuário, a família, o papel e o horário de expiração."""
    exp = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode({"sub": user_id, "fam": family_id, "role": role, "exp": exp}, secret, algorithm="HS256")


def decode_token(secret: str, token: str) -> dict[str, Any]:
    """Confere a assinatura e a validade do JWT e devolve seu conteúdo; lança erro se for inválido."""
    return jwt.decode(token, secret, algorithms=["HS256"])
