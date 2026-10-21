"""Testes da exclusão de conta e de família.

Este arquivo garante que o último admin não pode sair, que outros usuários podem apagar a própria conta, que a
senha é exigida e tem limite de tentativas, que só o admin apaga a família e que isso remove todos os dados e
contas dela sem tocar em outras famílias. Também garante que o e-mail pode ser usado de novo depois.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import auth as auth_module
from app.repositories.memory import InMemoryRepository
from tests.test_dados import DESP, _add_user, _signup

SENHA = {"senha": "senha-forte-1"}


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    """Zera o contador de senhas erradas antes de cada teste, para um teste não bloquear o outro."""
    auth_module._failures.clear()


def _excluir(client: TestClient, caminho: str, h: dict[str, str], senha: str = "senha-forte-1"):  # type: ignore[no-untyped-def]
    """Envia um DELETE com a senha no corpo para a rota informada."""
    return client.request("DELETE", f"/api/v1/{caminho}", headers=h, json={"senha": senha})


def _entra(client: TestClient, email: str, senha: str = "senha-forte-1") -> int:
    """Tenta fazer login e devolve só o status HTTP."""
    return client.post("/api/v1/auth/login", json={"email": email, "senha": senha}).status_code


def test_ultimo_admin_nao_pode_excluir_a_conta(client: TestClient) -> None:
    """Verifica que o único admin recebe 409 ao tentar sair e continua conseguindo entrar."""
    admin = _signup(client, "a@x.com")
    r = _excluir(client, "conta", admin)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ultimo_admin"
    assert "Exclua a família" in r.json()["error"]["message"]
    assert _entra(client, "a@x.com") == 200


def test_ultimo_admin_barrado_mesmo_com_outros_membros(client: TestClient) -> None:
    """Verifica que o único admin é barrado mesmo havendo membros comuns na família."""
    admin = _signup(client, "a@x.com")
    _add_user(client, admin, "m@x.com", "membro")
    assert _excluir(client, "conta", admin).status_code == 409


def test_admin_pode_sair_se_houver_outro_admin(client: TestClient) -> None:
    """Verifica que um admin pode sair quando existe outro admin."""
    admin = _signup(client, "a@x.com")
    _add_user(client, admin, "b@x.com", "admin")
    assert _excluir(client, "conta", admin).status_code == 204
    assert _entra(client, "a@x.com") == 401
    assert _entra(client, "b@x.com") == 200


def test_membro_exclui_a_propria_conta_e_a_familia_continua(client: TestClient) -> None:
    """Verifica que o membro some, o token dele para de valer e os dados da família continuam."""
    admin = _signup(client, "a@x.com")
    membro = _add_user(client, admin, "m@x.com", "membro")
    client.post("/api/v1/despesas", headers=admin, json=DESP)
    assert _excluir(client, "conta", membro).status_code == 204
    assert _entra(client, "m@x.com") == 401
    assert client.get("/api/v1/despesas", headers=membro).status_code == 401
    assert client.get("/api/v1/usuarios", headers=admin).json()[0]["email"] == "a@x.com"
    assert len(client.get("/api/v1/despesas", headers=admin).json()) == 1


def test_senha_errada_nao_exclui_nada(client: TestClient) -> None:
    """Verifica que a senha errada responde 403 e não apaga conta nem família."""
    admin = _signup(client, "a@x.com")
    membro = _add_user(client, admin, "m@x.com", "membro")
    r = _excluir(client, "conta", membro, senha="errada-errada")
    assert (r.status_code, r.json()["error"]["code"]) == (403, "senha_incorreta")
    assert _excluir(client, "familia", admin, senha="errada-errada").status_code == 403
    assert _entra(client, "m@x.com") == 200 and _entra(client, "a@x.com") == 200


def test_tentativas_de_senha_tem_limite(client: TestClient) -> None:
    """Verifica que, depois de 5 senhas erradas, a exclusão é barrada com 429."""
    admin = _signup(client, "a@x.com")
    for _ in range(5):
        assert _excluir(client, "familia", admin, senha="errada-errada").status_code == 403
    assert _excluir(client, "familia", admin).status_code == 429


def test_so_admin_exclui_a_familia(client: TestClient) -> None:
    """Verifica que membro e leitor recebem 403 e quem não está logado recebe 401."""
    admin = _signup(client, "a@x.com")
    for papel in ("membro", "leitor"):
        h = _add_user(client, admin, f"{papel}@x.com", papel)
        assert _excluir(client, "familia", h).status_code == 403
    assert _excluir(client, "familia", {}).status_code == 401


def test_excluir_familia_apaga_tudo_e_so_dela(client: TestClient, repo: InMemoryRepository) -> None:
    """Verifica que excluir a família apaga todas as coleções e contas dela e não toca na outra família."""
    admin = _signup(client, "a@x.com", "Casa A")
    _add_user(client, admin, "m@x.com", "membro")
    outra = _signup(client, "b@x.com", "Casa B")
    for h in (admin, outra):
        client.post("/api/v1/categorias", headers=h, json={"nome": "Mercado", "cor": "#12b76a", "meta": 900})
        client.post("/api/v1/despesas", headers=h, json=DESP)
        client.put("/api/v1/integracoes/asaas", headers=h, json={"ambiente": "sandbox", "apiKey": "chave-secreta-123"})
        client.get("/api/v1/backup", headers=h)
    fam_a = client.get("/api/v1/auth/me", headers=admin).json()["familyId"]

    assert _excluir(client, "familia", admin).status_code == 204

    for colecao in ("despesas", "categorias", "configuracoes", "integracoes", "backups", "perfis"):
        assert repo.list(colecao, fam_a) == [], colecao
    assert repo.get("familias", "_root", fam_a) is None
    assert _entra(client, "a@x.com") == 401 and _entra(client, "m@x.com") == 401
    assert client.get("/api/v1/despesas", headers=admin).status_code == 401

    assert len(client.get("/api/v1/despesas", headers=outra).json()) == 1
    assert client.get("/api/v1/dados", headers=outra).json()["config"]["familia"] == "Casa B"


def test_email_pode_ser_reaproveitado_depois_de_excluir_a_familia(client: TestClient) -> None:
    """Verifica que o e-mail fica livre para um novo cadastro depois que a família é excluída."""
    admin = _signup(client, "a@x.com")
    assert _excluir(client, "familia", admin).status_code == 204
    _signup(client, "a@x.com", "Nova")
