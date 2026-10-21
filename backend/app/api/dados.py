"""Rotas dos dados financeiros da família.

Este arquivo cria as rotas de listar, criar, criar em lote, atualizar e excluir para despesas, categorias, tipos,
bancos e centros de custo. Em vez de repetir o código, um único gerador monta as rotas de cada recurso a partir
da tabela RECURSOS, que também diz quais papéis podem gravar.
Também cuida das configurações da família, da geração das despesas recorrentes de um novo mês e da rota /dados,
que entrega tudo o que o front precisa numa chamada só.
Quem usa: main.py inclui estas rotas; api/backup.py reaproveita os modelos e a leitura das configurações.
"""

from datetime import date, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, current_user, get_repository, require_roles
from app.core.errors import NotFoundError
from app.repositories.base import Doc, Repository

router = APIRouter(prefix="/api/v1", tags=["dados"])

Texto = Annotated[str, Field(max_length=120)]
Nome = Annotated[str, Field(min_length=1, max_length=80)]
Cor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Competencia = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
LOTE_MAX = 500


class _Base(BaseModel):
    """Modelo base que recusa campos desconhecidos e tira espaços das pontas dos textos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DespesaIn(_Base):
    """Uma despesa da família, com valor, classificação, competência, vencimento e situação."""

    descricao: Annotated[str, Field(min_length=1, max_length=120)]
    valor: Annotated[float, Field(ge=0, le=1_000_000_000)]
    centro: Texto = "Família"
    grupo: Texto = ""
    categoria: Texto = "Outros Gastos"
    tipo: Texto = "VARIAVEIS"
    banco: Texto = ""
    transacao: Texto = ""
    dtpg: Texto = ""
    status: Literal["ABERTO", "PAGO"] = "ABERTO"
    competencia: Competencia
    vencimento: date | None = None
    pagoEm: date | None = None
    recorrente: bool = False
    origemId: Texto = ""


class CategoriaIn(_Base):
    """Uma categoria de despesa, com cor e meta de gasto."""

    nome: Nome
    cor: Cor = "#2f6bff"
    meta: Annotated[float, Field(ge=0, le=1_000_000_000)] = 0


class TipoIn(_Base):
    """Um tipo de despesa, com cor e descrição."""

    nome: Nome
    cor: Cor = "#64748b"
    desc: Texto = ""


class BancoIn(_Base):
    """Um banco ou conta usado para pagar despesas."""

    nome: Nome
    ativo: bool = True


class CentroIn(_Base):
    """Um centro de custo, como uma pessoa ou área da família."""

    nome: Nome


class ConfigIn(_Base):
    """Configurações da família: orçamento, renda, nome, dia de fechamento e alertas."""

    orcamento: Annotated[float, Field(ge=0, le=1_000_000_000)] = 0
    renda: Annotated[float, Field(ge=0, le=1_000_000_000)] = 0
    familia: Nome = "Minha Família"
    fechamento: Annotated[int, Field(ge=1, le=31)] = 31
    alertaPct: Annotated[float, Field(ge=0, le=100)] = 80
    reservaMeta: Annotated[float, Field(ge=0, le=100)] = 6
    somAtivo: bool = True


RECURSOS: dict[str, tuple[type[_Base], tuple[str, ...]]] = {
    "despesas": (DespesaIn, ("admin", "membro")),
    "categorias": (CategoriaIn, ("admin",)),
    "tipos": (TipoIn, ("admin",)),
    "bancos": (BancoIn, ("admin",)),
    "centros": (CentroIn, ("admin",)),
}


def _dump(model: _Base) -> Doc:
    """Converte o modelo em dicionário pronto para JSON, com datas como texto."""
    return model.model_dump(mode="json")


def _public(doc: Doc) -> Doc:
    """Tira o familyId do documento antes de devolvê-lo ao cliente."""
    return {k: v for k, v in doc.items() if k != "familyId"}


def _register(nome: str, model: type[_Base], writers: tuple[str, ...]) -> None:
    """Cria as cinco rotas de um recurso (listar, criar, criar em lote, atualizar e excluir).
    Leitura é liberada a qualquer usuário logado; gravação só aos papéis em writers.
    No lote, se uma gravação falhar no meio, os itens já criados são apagados antes de devolver o erro.
    """
    writer = require_roles(*writers)

    @router.get(f"/{nome}", name=f"listar_{nome}")
    def listar(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)) -> list[Doc]:
        return [_public(d) for d in repo.list(nome, user.family_id)]

    @router.post(f"/{nome}", status_code=201, name=f"criar_{nome}")
    def criar(
        body: model,  # type: ignore[valid-type]
        user: CurrentUser = Depends(writer),
        repo: Repository = Depends(get_repository),
    ) -> Doc:
        return _public(repo.create(nome, user.family_id, _dump(body)))

    @router.post(f"/{nome}/lote", status_code=201, name=f"criar_lote_{nome}")
    def criar_lote(
        body: Annotated[list[model], Field(min_length=1, max_length=LOTE_MAX)],  # type: ignore[valid-type]
        user: CurrentUser = Depends(writer),
        repo: Repository = Depends(get_repository),
    ) -> list[Doc]:
        criados: list[Doc] = []
        try:
            for item in body:
                criados.append(repo.create(nome, user.family_id, _dump(item)))
        except Exception:
            for doc in criados:
                repo.delete(nome, user.family_id, doc["id"])
            raise
        return [_public(d) for d in criados]

    @router.put(f"/{nome}/{{item_id}}", name=f"atualizar_{nome}")
    def atualizar(
        item_id: str,
        body: model,  # type: ignore[valid-type]
        user: CurrentUser = Depends(writer),
        repo: Repository = Depends(get_repository),
    ) -> Doc:
        updated = repo.update(nome, user.family_id, item_id, _dump(body))
        if updated is None:
            raise NotFoundError(nome.capitalize())
        return _public(updated)

    @router.delete(f"/{nome}/{{item_id}}", status_code=204, name=f"excluir_{nome}")
    def excluir(item_id: str, user: CurrentUser = Depends(writer), repo: Repository = Depends(get_repository)) -> None:
        if not repo.delete(nome, user.family_id, item_id):
            raise NotFoundError(nome.capitalize())


for _nome, (_model, _writers) in RECURSOS.items():
    _register(_nome, _model, _writers)

_DOCS = {
    "listar_{n}": "Lista {n} da família.",
    "criar_{n}": "Cria um item em {n}.",
    "criar_lote_{n}": "Cria vários itens de {n} de uma vez (tudo ou nada).",
    "atualizar_{n}": "Atualiza um item de {n}.",
    "excluir_{n}": "Exclui um item de {n}.",
}
for _rota in router.routes:
    for _modelo, _texto in _DOCS.items():
        for _nome in RECURSOS:
            if getattr(_rota, "name", "") == _modelo.format(n=_nome):
                _rota.endpoint.__doc__ = _texto.format(n=_nome)  # type: ignore[attr-defined]


class GerarMesIn(_Base):
    """Mês (competência no formato AAAA-MM) para o qual gerar as despesas recorrentes."""

    competencia: Competencia


def _mes_anterior(competencia: str) -> str:
    """Devolve a competência do mês anterior, virando o ano em janeiro."""
    ano, mes = int(competencia[:4]), int(competencia[5:])
    return f"{ano - 1}-12" if mes == 1 else f"{ano}-{mes - 1:02d}"


def _mesmo_dia_em(competencia: str, vencimento: str | None) -> str | None:
    """Leva o dia do vencimento para a nova competência, usando o último dia do mês quando ele for mais curto."""
    if not vencimento:
        return None
    ano, mes = int(competencia[:4]), int(competencia[5:])
    ultimo = (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)).day
    return date(ano, mes, min(int(vencimento[8:10]), ultimo)).isoformat()


@router.post("/despesas/gerar-mes", status_code=201)
def gerar_mes(
    body: GerarMesIn,
    user: CurrentUser = Depends(require_roles("admin", "membro")),
    repo: Repository = Depends(get_repository),
) -> list[Doc]:
    """Copia para a competência as despesas recorrentes do mês anterior. Idempotente: não duplica."""
    todas = repo.list("despesas", user.family_id)
    ja_geradas = {d.get("origemId") for d in todas if d.get("competencia") == body.competencia}
    criadas: list[Doc] = []
    for origem in todas:
        if origem.get("competencia") != _mes_anterior(body.competencia) or not origem.get("recorrente"):
            continue
        if origem["id"] in ja_geradas:
            continue
        nova = {
            **{k: v for k, v in origem.items() if k in DespesaIn.model_fields},
            "competencia": body.competencia,
            "vencimento": _mesmo_dia_em(body.competencia, origem.get("vencimento")),
            "status": "ABERTO",
            "pagoEm": None,
            "origemId": origem["id"],
        }
        criadas.append(_public(repo.create("despesas", user.family_id, _dump(DespesaIn(**nova)))))
    return criadas


def config_id(family_id: str) -> str:
    """Devolve o id fixo do documento de configurações da família."""
    return f"config_{family_id}"


def read_config(repo: Repository, family_id: str) -> Doc:
    """Devolve as configurações da família completando com os valores padrão.
    O nome da família vem do cadastro da família, mas um nome salvo nas configurações tem prioridade.
    """
    doc = repo.get("configuracoes", family_id, config_id(family_id))
    base = _dump(ConfigIn())
    familia = repo.get("familias", "_root", family_id)
    if familia and familia.get("nome"):
        base["familia"] = familia["nome"]
    return {**base, **{k: v for k, v in (doc or {}).items() if k in base}}


@router.get("/configuracoes")
def obter_config(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)) -> Doc:
    """Configurações da família (orçamento, renda, alertas, nome)."""
    return read_config(repo, user.family_id)


@router.put("/configuracoes")
def salvar_config(
    body: ConfigIn, user: CurrentUser = Depends(require_roles("admin")), repo: Repository = Depends(get_repository)
) -> Doc:
    """Salva as configurações da família."""
    data = _dump(body)
    if repo.update("configuracoes", user.family_id, config_id(user.family_id), data) is None:
        repo.create("configuracoes", user.family_id, data, doc_id=config_id(user.family_id))
    return read_config(repo, user.family_id)


@router.get("/dados")
def dados(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)) -> dict[str, Any]:
    """Tudo o que o front precisa para abrir, em uma chamada."""
    out: dict[str, Any] = {nome: [_public(d) for d in repo.list(nome, user.family_id)] for nome in RECURSOS}
    out["config"] = read_config(repo, user.family_id)
    perfis = repo.list("perfis", user.family_id)
    out["usuarios"] = [
        {
            "id": p["id"],
            "nome": p["nome"],
            "papel": p["papel"],
            **({"email": p["email"]} if user.role == "admin" else {}),
        }
        for p in perfis
    ]
    out["eu"] = {"id": user.id, "papel": user.role}
    return out
