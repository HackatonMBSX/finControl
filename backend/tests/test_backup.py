"""Testes de backup e restauração.

Este arquivo garante que exportar e restaurar devolve os mesmos dados, que a restauração guarda antes um backup
automático, que arquivos adulterados, de outra versão ou com registros inválidos são recusados sem mudar nada,
que só o admin usa essas rotas, que outra família não é afetada, que o histórico guarda só os últimos backups e
que um arquivo regravado pelo navegador (números como 3600 em vez de 3600.0) continua válido.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import auth as auth_module
from tests.test_dados import DESP, _add_user, _signup

H = dict[str, str]


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    """Zera o contador de senhas erradas antes de cada teste, para um teste não bloquear o outro."""
    auth_module._failures.clear()


def _popular(client: TestClient, h: H) -> None:
    """Preenche a família com cadastros, despesas, uma recorrente gerada e configurações."""
    client.post("/api/v1/categorias", headers=h, json={"nome": "Mercado", "cor": "#12b76a", "meta": 900})
    client.post("/api/v1/bancos", headers=h, json={"nome": "Banco X"})
    client.post("/api/v1/centros", headers=h, json={"nome": "Família"})
    client.post("/api/v1/despesas", headers=h, json=DESP)
    client.post("/api/v1/despesas", headers=h, json={**DESP, "descricao": "Luz", "valor": 180.5, "recorrente": False})
    client.post("/api/v1/despesas/gerar-mes", headers=h, json={"competencia": "2026-11"})
    cfg = client.get("/api/v1/configuracoes", headers=h).json()
    client.put("/api/v1/configuracoes", headers=h, json={**cfg, "orcamento": 9000, "familia": "Casa Silva"})


def _estado(client: TestClient, h: H) -> dict[str, Any]:
    """Resume os dados da família ignorando ids e datas, para comparar o antes e o depois.
    As despesas geradas são ligadas à origem pela descrição, já que os ids mudam ao restaurar.
    """
    d = client.get("/api/v1/dados", headers=h).json()
    nome = {x["id"]: x["descricao"] + x["competencia"] for x in d["despesas"]}
    out: dict[str, Any] = {"config": d["config"]}
    for k in ("categorias", "tipos", "bancos", "centros"):
        out[k] = sorted(
            tuple(sorted((a, str(b)) for a, b in x.items() if a not in ("id", "createdAt", "updatedAt"))) for x in d[k]
        )
    out["despesas"] = sorted(
        (
            tuple(sorted((a, str(b)) for a, b in x.items() if a not in ("id", "origemId", "createdAt", "updatedAt"))),
            nome.get(x["origemId"], ""),
        )
        for x in d["despesas"]
    )
    return out


def test_exportar_apagar_restaurar_devolve_os_mesmos_dados(client: TestClient) -> None:
    """Verifica que apagar tudo e restaurar o arquivo exportado devolve exatamente os mesmos dados."""
    h = _signup(client, "adm@example.com")
    _popular(client, h)
    antes = _estado(client, h)
    assert len(antes["despesas"]) == 3

    arquivo = client.get("/api/v1/backup", headers=h).json()
    assert arquivo["versao"] == 1 and len(arquivo["checksum"]) == 64

    for d in client.get("/api/v1/despesas", headers=h).json():
        client.delete(f"/api/v1/despesas/{d['id']}", headers=h)
    for c in client.get("/api/v1/categorias", headers=h).json():
        client.delete(f"/api/v1/categorias/{c['id']}", headers=h)
    assert client.get("/api/v1/despesas", headers=h).json() == []

    r = client.post("/api/v1/backup/restore", headers=h, json=arquivo)
    assert r.status_code == 200, r.text
    assert r.json()["restaurado"]["despesas"] == 3
    assert _estado(client, h) == antes


def test_restaurar_cria_backup_automatico_no_historico(client: TestClient) -> None:
    """Verifica que a restauração guarda o estado anterior no histórico e que ele pode ser restaurado."""
    h = _signup(client, "adm@example.com")
    _popular(client, h)
    arquivo = client.get("/api/v1/backup", headers=h).json()
    client.post("/api/v1/despesas", headers=h, json={**DESP, "descricao": "Extra"})
    r = client.post("/api/v1/backup/restore", headers=h, json=arquivo).json()

    hist = client.get("/api/v1/backup/historico", headers=h).json()
    auto = next(x for x in hist if x["id"] == r["backupAutomaticoId"])
    assert "automático" in auto["motivo"] and auto["contagens"]["despesas"] == 4
    assert "conteudo" not in auto
    guardado = client.get(f"/api/v1/backup/historico/{auto['id']}", headers=h).json()
    assert len(guardado["dados"]["despesas"]) == 4

    voltou = client.post("/api/v1/backup/restore", headers=h, json=guardado)
    assert voltou.status_code == 200
    assert len(client.get("/api/v1/despesas", headers=h).json()) == 4


def test_arquivo_adulterado_e_recusado_e_nada_muda(client: TestClient) -> None:
    """Verifica que um arquivo alterado falha no checksum e os dados ficam como estavam."""
    h = _signup(client, "adm@example.com")
    _popular(client, h)
    arquivo = client.get("/api/v1/backup", headers=h).json()
    antes = _estado(client, h)

    arquivo["dados"]["despesas"][0]["valor"] = 1
    r = client.post("/api/v1/backup/restore", headers=h, json=arquivo)
    assert r.status_code == 422 and r.json()["error"]["code"] == "backup_invalido"
    assert "checksum" in r.json()["error"]["message"]
    assert _estado(client, h) == antes


@pytest.mark.parametrize(
    "mutar, trecho",
    [
        (lambda a: a.update(versao=99), "Versão 99"),
        (lambda a: a.update(app="outro"), "não é um backup"),
        (lambda a: a.pop("dados"), "incompleto"),
        (lambda a: a.update(checksum="0" * 64), "checksum"),
    ],
)
def test_formatos_invalidos(client: TestClient, mutar: Any, trecho: str) -> None:
    """Verifica que versão, app, dados ou checksum errados são recusados com a mensagem certa."""
    h = _signup(client, "adm@example.com")
    arquivo = client.get("/api/v1/backup", headers=h).json()
    mutar(arquivo)
    r = client.post("/api/v1/backup/restore", headers=h, json=arquivo)
    assert r.status_code == 422 and trecho in r.json()["error"]["message"]


def test_registro_invalido_com_checksum_correto_tambem_e_recusado(client: TestClient) -> None:
    """Verifica que um registro inválido é recusado mesmo com checksum recalculado."""
    from app.api.backup import _checksum

    h = _signup(client, "adm@example.com")
    arquivo = client.get("/api/v1/backup", headers=h).json()
    arquivo["dados"]["despesas"] = [{"id": "x", "descricao": "", "valor": -5, "competencia": "2026-13"}]
    arquivo["checksum"] = _checksum(1, arquivo["dados"], arquivo["config"])
    r = client.post("/api/v1/backup/restore", headers=h, json=arquivo)
    assert r.status_code == 422 and "despesas #1" in r.json()["error"]["message"]


def test_so_admin_exporta_e_restaura(client: TestClient) -> None:
    """Verifica que membro e leitor recebem 403 e quem não está logado recebe 401."""
    adm = _signup(client, "adm@example.com")
    membro = _add_user(client, adm, "m@example.com", "membro")
    leitor = _add_user(client, adm, "l@example.com", "leitor")
    arquivo = client.get("/api/v1/backup", headers=adm).json()
    for h in (membro, leitor):
        assert client.get("/api/v1/backup", headers=h).status_code == 403
        assert client.get("/api/v1/backup/historico", headers=h).status_code == 403
        assert client.post("/api/v1/backup/restore", headers=h, json=arquivo).status_code == 403
    assert client.get("/api/v1/backup").status_code == 401


def test_restaurar_nao_toca_em_outra_familia(client: TestClient) -> None:
    """Verifica que restaurar não altera os dados nem o histórico de outra família."""
    a = _signup(client, "a@example.com", familia="Família A")
    b = _signup(client, "b@example.com", familia="Família B")
    client.post("/api/v1/despesas", headers=b, json=DESP)
    _popular(client, a)
    arquivo = client.get("/api/v1/backup", headers=a).json()
    client.post("/api/v1/backup/restore", headers=a, json=arquivo)
    assert len(client.get("/api/v1/despesas", headers=b).json()) == 1
    assert client.get("/api/v1/backup/historico", headers=b).json() == []


def test_historico_guarda_so_os_ultimos(client: TestClient) -> None:
    """Verifica que o histórico fica com 10 backups e que um id inexistente responde 404."""
    h = _signup(client, "adm@example.com")
    for _ in range(12):
        client.get("/api/v1/backup", headers=h)
    assert len(client.get("/api/v1/backup/historico", headers=h).json()) == 10
    assert client.get("/api/v1/backup/historico/inexistente", headers=h).status_code == 404


def test_falha_no_meio_da_restauracao_aponta_para_o_backup_automatico(
    client: TestClient, repo: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica que uma falha no meio responde 500 e deixa o backup automático no histórico."""
    h = _signup(client, "adm@example.com")
    _popular(client, h)
    arquivo = client.get("/api/v1/backup", headers=h).json()
    original = repo.create
    chamadas = {"n": 0}

    def quebra(*a: Any, **kw: Any) -> Any:
        """Deixa passar as duas primeiras gravações e falha nas seguintes, simulando o banco caindo."""
        chamadas["n"] += 1
        if chamadas["n"] > 2:
            raise RuntimeError("Appwrite caiu")
        return original(*a, **kw)

    monkeypatch.setattr(repo, "create", quebra)
    r = client.post("/api/v1/backup/restore", headers=h, json=arquivo)
    assert r.status_code == 500 and r.json()["error"]["code"] == "restauracao_falhou"
    monkeypatch.setattr(repo, "create", original)
    hist = client.get("/api/v1/backup/historico", headers=h).json()
    assert any("automático" in x["motivo"] for x in hist)


def test_arquivo_regravado_pelo_navegador_continua_valido(client: TestClient) -> None:
    """Verifica que trocar 3600.0 por 3600 no arquivo não quebra o checksum."""
    import json

    h = _signup(client, "adm@example.com")
    _popular(client, h)
    texto = client.get("/api/v1/backup", headers=h).text
    assert "3600.0" in texto
    regravado = json.loads(texto.replace("3600.0", "3600"))
    r = client.post("/api/v1/backup/restore", headers=h, json=regravado)
    assert r.status_code == 200, r.text
