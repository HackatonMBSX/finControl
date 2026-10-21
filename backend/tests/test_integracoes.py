"""Testes da integração com o Asaas.

Este arquivo garante que a chave do Asaas é guardada cifrada e só aparece mascarada, que enviar chave vazia mantém
a anterior, que o teste de conexão não finge uma conexão real, que só o admin pode salvar, que cada família tem
a própria configuração e que a cifra só abre com o segredo certo.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import auth as auth_module
from app.core.secrets import decrypt, encrypt
from app.repositories.memory import InMemoryRepository

URL = "/api/v1/integracoes/asaas"
CHAVE = "sk_teste_1234567890abcd"


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    """Zera o contador de senhas erradas antes de cada teste, para um teste não bloquear o outro."""
    auth_module._failures.clear()


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    """Cadastra uma família e entrega o cabeçalho de autorização do admin."""
    r = client.post(
        "/api/v1/auth/register",
        json={"familia": "Casa", "nome": "Admin", "email": "a@x.com", "senha": "senha-forte-1"},
    )
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}


def test_padrao_vazio_e_desconectado(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que, sem nada salvo, a integração aparece desconectada e sem chave."""
    assert client.get(URL, headers=admin).json() == {
        "conectado": False,
        "ambiente": "sandbox",
        "temChave": False,
        "chaveMascarada": "",
    }


def test_salva_chave_cifrada_e_so_mostra_final(
    client: TestClient, repo: InMemoryRepository, admin: dict[str, str]
) -> None:
    """Verifica que a chave vai cifrada para o banco e a resposta mostra só os 4 últimos caracteres."""
    r = client.put(URL, headers=admin, json={"conectado": True, "ambiente": "producao", "apiKey": CHAVE})
    assert r.status_code == 200
    out = r.json()
    assert out == {"conectado": True, "ambiente": "producao", "temChave": True, "chaveMascarada": "••••abcd"}
    assert CHAVE not in r.text and CHAVE not in client.get(URL, headers=admin).text

    guardado = next(iter(repo._data["integracoes"].values()))
    assert CHAVE not in str(guardado)
    assert guardado["apiKeyCifrada"].startswith("gAAAA")


def test_chave_vazia_mantem_a_anterior(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que salvar com chave vazia mantém a chave antiga e uma nova a substitui."""
    client.put(URL, headers=admin, json={"conectado": True, "apiKey": CHAVE})
    out = client.put(URL, headers=admin, json={"conectado": False, "ambiente": "sandbox", "apiKey": ""}).json()
    assert out["conectado"] is False and out["temChave"] is True and out["chaveMascarada"] == "••••abcd"
    out = client.put(URL, headers=admin, json={"conectado": True, "apiKey": "sk_nova_zzzz9999"}).json()
    assert out["chaveMascarada"] == "••••9999"


def test_testar_exige_chave_e_nao_finge_conexao(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que o teste falha sem chave e, com chave, avisa que a conexão real ainda não está ativa."""
    sem = client.post(f"{URL}/testar", headers=admin).json()
    assert sem["ok"] is False
    client.put(URL, headers=admin, json={"conectado": True, "apiKey": CHAVE})
    com = client.post(f"{URL}/testar", headers=admin).json()
    assert com["ok"] is True and "ainda não está ativa" in com["mensagem"]
    assert "ms" not in com


def test_validacao_e_permissoes(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que dados inválidos dão 422, sem login dá 401 e o leitor pode ver mas não salvar."""
    assert client.put(URL, headers=admin, json={"ambiente": "lua"}).status_code == 422
    assert client.put(URL, headers=admin, json={"extra": 1}).status_code == 422
    assert client.get(URL).status_code == 401
    client.post(
        "/api/v1/usuarios",
        headers=admin,
        json={"nome": "Leitor", "email": "l@x.com", "senha": "senha-forte-1", "papel": "leitor"},
    )
    token = client.post("/api/v1/auth/login", json={"email": "l@x.com", "senha": "senha-forte-1"}).json()["accessToken"]
    leitor = {"Authorization": f"Bearer {token}"}
    assert client.get(URL, headers=leitor).status_code == 200
    assert client.put(URL, headers=leitor, json={"conectado": True}).status_code == 403


def test_familias_isoladas(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que outra família não enxerga a chave salva."""
    client.put(URL, headers=admin, json={"conectado": True, "apiKey": CHAVE})
    r = client.post(
        "/api/v1/auth/register",
        json={"familia": "Outra", "nome": "Bia", "email": "b@x.com", "senha": "senha-forte-1"},
    )
    outra = {"Authorization": f"Bearer {r.json()['accessToken']}"}
    assert client.get(URL, headers=outra).json()["temChave"] is False


def test_cifra_ida_e_volta_e_segredo_errado() -> None:
    """Verifica que o texto volta com o segredo certo e dá None com segredo errado ou token inválido."""
    token = encrypt("segredo-a", "texto")
    assert decrypt("segredo-a", token) == "texto"
    assert decrypt("segredo-b", token) is None
    assert decrypt("segredo-a", "lixo") is None
