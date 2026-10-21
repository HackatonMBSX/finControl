"""Testes das rotas de dados financeiros.

Este arquivo garante o CRUD (criar, ler, atualizar e apagar) de despesas e cadastros, a validação dos campos,
as permissões de cada papel, o isolamento entre famílias, as configurações, a rota /dados, a criação em lote (que desfaz
tudo se o banco falhar no meio) e a geração das despesas recorrentes de um novo mês.
Também testa a exclusão de usuários.
Quem usa: test_conta.py e test_backup.py reaproveitam DESP, _signup e _add_user daqui.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import auth as auth_module

DESP = {
    "descricao": "Aluguel",
    "valor": 3600,
    "categoria": "Alugueis",
    "tipo": "FIXA",
    "competencia": "2026-10",
    "vencimento": "2026-10-07",
    "recorrente": True,
}


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    """Zera o contador de senhas erradas antes de cada teste, para um teste não bloquear o outro."""
    auth_module._failures.clear()


def _signup(client: TestClient, email: str, familia: str = "Família") -> dict[str, str]:
    """Cadastra uma família pela API e devolve o cabeçalho de autorização do admin."""
    r = client.post(
        "/api/v1/auth/register", json={"familia": familia, "nome": "Admin", "email": email, "senha": "senha-forte-1"}
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}


def _add_user(client: TestClient, admin: dict[str, str], email: str, papel: str) -> dict[str, str]:
    """Cria um usuário com o papel informado, faz login com ele e devolve o cabeçalho de autorização."""
    r = client.post(
        "/api/v1/usuarios",
        headers=admin,
        json={"nome": papel.title(), "email": email, "senha": "senha-forte-1", "papel": papel},
    )
    assert r.status_code == 201, r.text
    login = client.post("/api/v1/auth/login", json={"email": email, "senha": "senha-forte-1"})
    return {"Authorization": f"Bearer {login.json()['accessToken']}"}


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    """Entrega o cabeçalho de autorização do admin de uma família nova."""
    return _signup(client, "admin@x.com")


def test_requires_login(client: TestClient) -> None:
    """Verifica que as rotas de dados exigem login."""
    for path in ("/api/v1/despesas", "/api/v1/categorias", "/api/v1/configuracoes", "/api/v1/dados"):
        assert client.get(path).status_code == 401


def test_despesa_crud(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica criar, listar, marcar como paga e excluir uma despesa, sem expor o familyId."""
    created = client.post("/api/v1/despesas", headers=admin, json=DESP)
    assert created.status_code == 201
    item = created.json()
    assert item["id"] and item["descricao"] == "Aluguel" and "familyId" not in item
    assert item["status"] == "ABERTO" and item["vencimento"] == "2026-10-07"

    listed = client.get("/api/v1/despesas", headers=admin).json()
    assert [d["id"] for d in listed] == [item["id"]]

    pago = {**DESP, "status": "PAGO", "pagoEm": "2026-10-06"}
    upd = client.put(f"/api/v1/despesas/{item['id']}", headers=admin, json=pago)
    assert upd.status_code == 200 and upd.json()["status"] == "PAGO" and upd.json()["pagoEm"] == "2026-10-06"

    assert client.delete(f"/api/v1/despesas/{item['id']}", headers=admin).status_code == 204
    assert client.get("/api/v1/despesas", headers=admin).json() == []


@pytest.mark.parametrize(
    "mudanca",
    [
        {"valor": -1},
        {"descricao": ""},
        {"competencia": "2026-13"},
        {"competencia": "outubro"},
        {"vencimento": "07/10/2026"},
        {"status": "TALVEZ"},
        {"campo_extra": "x"},
    ],
)
def test_despesa_validation(client: TestClient, admin: dict[str, str], mudanca: dict) -> None:
    """Verifica que cada despesa com campo inválido ou extra responde 422."""
    r = client.post("/api/v1/despesas", headers=admin, json={**DESP, **mudanca})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_not_found(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que atualizar ou excluir um id inexistente responde 404."""
    assert client.put("/api/v1/despesas/nao-existe", headers=admin, json=DESP).status_code == 404
    assert client.delete("/api/v1/despesas/nao-existe", headers=admin).status_code == 404


def test_families_are_isolated(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que outra família não vê, não altera e não apaga a despesa."""
    item = client.post("/api/v1/despesas", headers=admin, json=DESP).json()
    other = _signup(client, "outra@x.com", familia="Outra")
    assert client.get("/api/v1/despesas", headers=other).json() == []
    assert client.put(f"/api/v1/despesas/{item['id']}", headers=other, json=DESP).status_code == 404
    assert client.delete(f"/api/v1/despesas/{item['id']}", headers=other).status_code == 404
    assert len(client.get("/api/v1/despesas", headers=admin).json()) == 1


def test_roles(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que membro grava despesas mas não cadastros, e que leitor só lê."""
    membro = _add_user(client, admin, "membro@x.com", "membro")
    leitor = _add_user(client, admin, "leitor@x.com", "leitor")

    assert client.post("/api/v1/despesas", headers=membro, json=DESP).status_code == 201
    assert client.post("/api/v1/despesas", headers=leitor, json=DESP).status_code == 403
    assert client.get("/api/v1/despesas", headers=leitor).status_code == 200

    cat = {"nome": "Pets", "cor": "#112233", "meta": 100}
    assert client.post("/api/v1/categorias", headers=membro, json=cat).status_code == 403
    assert client.post("/api/v1/categorias", headers=admin, json=cat).status_code == 201
    assert client.put("/api/v1/configuracoes", headers=membro, json={"orcamento": 1}).status_code == 403


@pytest.mark.parametrize(
    ("recurso", "corpo"),
    [
        ("categorias", {"nome": "Pets", "cor": "#aabbcc", "meta": 150}),
        ("tipos", {"nome": "ANUAL", "cor": "#123456", "desc": "Uma vez por ano"}),
        ("bancos", {"nome": "Banco X", "ativo": True}),
        ("centros", {"nome": "Avó"}),
    ],
)
def test_cadastros_crud(client: TestClient, admin: dict[str, str], recurso: str, corpo: dict) -> None:
    """Verifica criar, listar, renomear e excluir cada tipo de cadastro."""
    r = client.post(f"/api/v1/{recurso}", headers=admin, json=corpo)
    assert r.status_code == 201
    item_id = r.json()["id"]
    assert client.get(f"/api/v1/{recurso}", headers=admin).json()[0]["nome"] == corpo["nome"]
    renamed = {**corpo, "nome": "Renomeado"}
    assert client.put(f"/api/v1/{recurso}/{item_id}", headers=admin, json=renamed).json()["nome"] == "Renomeado"
    assert client.delete(f"/api/v1/{recurso}/{item_id}", headers=admin).status_code == 204


def test_categoria_cor_invalida(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que uma cor fora do formato #RRGGBB responde 422."""
    r = client.post("/api/v1/categorias", headers=admin, json={"nome": "X", "cor": "vermelho"})
    assert r.status_code == 422


def test_config_defaults_and_save(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica os valores padrão das configurações, o salvamento repetido e a recusa de dia de fechamento inválido."""
    padrao = client.get("/api/v1/configuracoes", headers=admin).json()
    assert padrao["alertaPct"] == 80 and padrao["somAtivo"] is True

    nova = {**padrao, "orcamento": 25000, "renda": 28500, "familia": "Casa Silva", "alertaPct": 70}
    assert client.put("/api/v1/configuracoes", headers=admin, json=nova).json()["orcamento"] == 25000
    again = client.put("/api/v1/configuracoes", headers=admin, json={**nova, "orcamento": 26000})
    assert again.status_code == 200 and again.json()["orcamento"] == 26000
    assert client.get("/api/v1/configuracoes", headers=admin).json()["familia"] == "Casa Silva"
    assert client.put("/api/v1/configuracoes", headers=admin, json={**nova, "fechamento": 40}).status_code == 422


def test_dados_bootstrap(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que /dados traz tudo e só mostra e-mails dos usuários para o admin."""
    client.post("/api/v1/despesas", headers=admin, json=DESP)
    leitor = _add_user(client, admin, "leitor@x.com", "leitor")

    full = client.get("/api/v1/dados", headers=admin).json()
    assert set(full) >= {"despesas", "categorias", "tipos", "bancos", "centros", "config", "usuarios", "eu"}
    assert len(full["despesas"]) == 1 and full["eu"]["papel"] == "admin"
    assert all("email" in u for u in full["usuarios"])

    reduzido = client.get("/api/v1/dados", headers=leitor).json()
    assert reduzido["eu"]["papel"] == "leitor"
    assert all("email" not in u for u in reduzido["usuarios"])


def test_lote_cria_varios_e_valida_tudo(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que o lote cria todos os itens e que um item inválido ou lista vazia não grava nada."""
    itens = [{**DESP, "descricao": f"Conta {i}"} for i in range(3)]
    r = client.post("/api/v1/despesas/lote", headers=admin, json=itens)
    assert r.status_code == 201 and len(r.json()) == 3
    assert len(client.get("/api/v1/despesas", headers=admin).json()) == 3
    ruim = [*itens, {**DESP, "valor": -5}]
    assert client.post("/api/v1/despesas/lote", headers=admin, json=ruim).status_code == 422
    assert len(client.get("/api/v1/despesas", headers=admin).json()) == 3
    assert client.post("/api/v1/despesas/lote", headers=admin, json=[]).status_code == 422


def test_lote_desfaz_o_que_criou_se_o_banco_falhar_no_meio(
    client: TestClient, repo: Any, admin: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica que, se o banco falhar no meio do lote, nenhum item do lote fica gravado."""
    original = repo.create
    chamadas = {"n": 0}

    def quebra(*a: Any, **kw: Any) -> Any:
        """Deixa passar as duas primeiras gravações e falha na terceira, simulando o banco caindo."""
        chamadas["n"] += 1
        if chamadas["n"] > 2:
            raise RuntimeError("Appwrite caiu")
        return original(*a, **kw)

    monkeypatch.setattr(repo, "create", quebra)
    itens = [{**DESP, "descricao": f"Conta {i}"} for i in range(3)]
    assert client.post("/api/v1/despesas/lote", headers=admin, json=itens).status_code == 500
    monkeypatch.setattr(repo, "create", original)
    assert client.get("/api/v1/despesas", headers=admin).json() == []


def test_gerar_mes_copia_recorrentes_sem_duplicar(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que só as recorrentes são copiadas, em aberto, com vencimento ajustado e sem duplicar."""
    fixa = client.post(
        "/api/v1/despesas", headers=admin, json={**DESP, "status": "PAGO", "pagoEm": "2026-10-06"}
    ).json()
    client.post("/api/v1/despesas", headers=admin, json={**DESP, "descricao": "Mercado", "recorrente": False})
    fim = {**DESP, "descricao": "Internet", "vencimento": "2026-10-31", "competencia": "2026-10"}
    client.post("/api/v1/despesas", headers=admin, json=fim)

    r = client.post("/api/v1/despesas/gerar-mes", headers=admin, json={"competencia": "2026-11"})
    assert r.status_code == 201
    novas = {d["descricao"]: d for d in r.json()}
    assert set(novas) == {"Aluguel", "Internet"}
    assert novas["Aluguel"]["status"] == "ABERTO" and novas["Aluguel"]["pagoEm"] is None
    assert novas["Aluguel"]["vencimento"] == "2026-11-07" and novas["Aluguel"]["origemId"] == fixa["id"]
    assert novas["Internet"]["vencimento"] == "2026-11-30"

    de_novo = client.post("/api/v1/despesas/gerar-mes", headers=admin, json={"competencia": "2026-11"})
    assert de_novo.json() == []
    assert len(client.get("/api/v1/despesas", headers=admin).json()) == 5


def test_gerar_mes_virada_de_ano_e_fevereiro(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica a virada de dezembro para janeiro, o fim de fevereiro e a recusa de competência malformada."""
    dez = {**DESP, "competencia": "2026-12", "vencimento": "2026-12-30"}
    client.post("/api/v1/despesas", headers=admin, json=dez)
    jan = client.post("/api/v1/despesas/gerar-mes", headers=admin, json={"competencia": "2027-01"}).json()
    assert jan[0]["vencimento"] == "2027-01-30"
    fev = client.post("/api/v1/despesas/gerar-mes", headers=admin, json={"competencia": "2027-02"}).json()
    assert fev[0]["vencimento"] == "2027-02-28"
    assert client.post("/api/v1/despesas/gerar-mes", headers=admin, json={"competencia": "2027-2"}).status_code == 422


def test_gerar_mes_leitor_nao_pode(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que o leitor não pode gerar as despesas do mês."""
    leitor = _add_user(client, admin, "leitor@x.com", "leitor")
    assert client.post("/api/v1/despesas/gerar-mes", headers=leitor, json={"competencia": "2026-11"}).status_code == 403


def test_excluir_usuario(client: TestClient, admin: dict[str, str]) -> None:
    """Verifica que o admin não exclui a si mesmo, o membro não exclui ninguém e o excluído não entra mais."""
    membro = _add_user(client, admin, "membro@x.com", "membro")
    usuarios = client.get("/api/v1/usuarios", headers=admin).json()
    meu = client.get("/api/v1/auth/me", headers=admin).json()["id"]
    alvo = next(u["id"] for u in usuarios if u["email"] == "membro@x.com")

    assert client.delete(f"/api/v1/usuarios/{meu}", headers=admin).status_code == 409
    assert client.delete(f"/api/v1/usuarios/{alvo}", headers=membro).status_code == 403
    assert client.delete(f"/api/v1/usuarios/{alvo}", headers=admin).status_code == 204
    assert client.delete(f"/api/v1/usuarios/{alvo}", headers=admin).status_code == 404
    login = client.post("/api/v1/auth/login", json={"email": "membro@x.com", "senha": "senha-forte-1"})
    assert login.status_code == 401


def test_nome_da_familia_do_cadastro_aparece_nas_configuracoes(client: TestClient) -> None:
    """Verifica que o nome dado no cadastro aparece nas configurações e pode ser trocado depois."""
    h = _signup(client, "casa@example.com", familia="Família Soares")
    assert client.get("/api/v1/configuracoes", headers=h).json()["familia"] == "Família Soares"
    assert client.get("/api/v1/dados", headers=h).json()["config"]["familia"] == "Família Soares"
    cfg = client.get("/api/v1/configuracoes", headers=h).json()
    novo = client.put("/api/v1/configuracoes", headers=h, json={**cfg, "familia": "Soares & Cia"})
    assert novo.status_code == 200 and novo.json()["familia"] == "Soares & Cia"
    assert client.get("/api/v1/configuracoes", headers=h).json()["familia"] == "Soares & Cia"


def test_duas_familias_salvam_config_e_asaas_sem_colidir(client: TestClient) -> None:
    """Verifica que duas famílias salvam configurações e chave do Asaas sem uma sobrescrever a outra."""
    a = _signup(client, "a@example.com", familia="Família A")
    b = _signup(client, "b@example.com", familia="Família B")
    for h, nome in ((a, "Casa A"), (b, "Casa B")):
        cfg = client.get("/api/v1/configuracoes", headers=h).json()
        assert client.put("/api/v1/configuracoes", headers=h, json={**cfg, "familia": nome}).status_code == 200
        assert (
            client.put(
                "/api/v1/integracoes/asaas", headers=h, json={"apiKey": f"chave-{nome[-1]}-xyz{nome[-1]}"}
            ).status_code
            == 200
        )
    assert client.get("/api/v1/configuracoes", headers=a).json()["familia"] == "Casa A"
    assert client.get("/api/v1/configuracoes", headers=b).json()["familia"] == "Casa B"
    assert client.get("/api/v1/integracoes/asaas", headers=a).json()["chaveMascarada"].endswith("zA")
    assert client.get("/api/v1/integracoes/asaas", headers=b).json()["chaveMascarada"].endswith("zB")
