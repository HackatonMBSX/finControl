# FinControl — controle de despesas familiares

Aplicativo web para a família saber **quanto já gastou**, **quanto ainda pode gastar** e **o que está para vencer**.
Projeto do Hackathon AMX (fase 2): front em HTML/CSS/JavaScript, API em Python (FastAPI) e banco NoSQL com
autenticação no Appwrite, publicado em VPS com Coolify.

- **Endereço publicado:** _a preencher depois da publicação no Coolify_
- **Versão:** 1.0.0 (candidata) · **Autor:** Alvaro Paiva Soares

## O que o sistema faz

Cadastro e login de famílias · perfis administrador, membro e leitor · despesas com quadro em 5 colunas (Atrasadas, Vence hoje,
Próx. 7 dias, Este mês, Pagas) e lista · gerar mês (recorrentes) · alertas visuais e sonoros · análises e orientações ·
cadastros e metas · tela de integração com o Asaas (preparada) · backup e restauração com checksum · exclusão de conta e de
família. Cada família só enxerga os próprios dados.

## Tecnologias

| Parte | Tecnologia |
| --- | --- |
| Front | HTML, CSS e JavaScript (ES modules), sem framework e sem build; servido pelo nginx |
| API | Python 3.13, FastAPI, Pydantic, JWT |
| Banco e login | Appwrite 2.5 (DocumentsDB sobre MongoDB 8.2 + Auth), Redis |
| Publicação | Docker Compose, Coolify |
| Testes | pytest, vitest, Playwright |

## Rodar com Docker (stack completa)

Pré-requisitos: Docker com Compose e cerca de 4 GB de RAM livres (o Appwrite é pesado). Na raiz do projeto:

```bash
cp .env.example .env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -hex 32)|;s|^APPWRITE_SECRET=.*|APPWRITE_SECRET=$(openssl rand -hex 24)|;s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 24)|" .env
docker compose up -d --build        # o Appwrite leva 1–2 min para ficar saudável; a API só inicia depois
```

Na primeira vez, crie o projeto e a chave de API no console do Appwrite (http://localhost:8081), preencha `APPWRITE_PROJECT_ID` e
`APPWRITE_API_KEY` no `.env` e rode `docker compose up -d api`. O passo a passo, a conferência e os problemas comuns estão em
[db/README.md](db/README.md).

| Serviço | Endereço local |
| --- | --- |
| App | http://localhost:8090 |
| API (a raiz abre o Swagger) | http://localhost:8091 |
| Console do Appwrite | http://localhost:8081 |

## Rodar sem Docker (desenvolvimento)

A API usa o repositório em memória, sem Appwrite: os dados somem ao reiniciar.

```bash
# API  → http://localhost:8000/docs
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
REPOSITORY_BACKEND=memory JWT_SECRET=troque-por-um-valor-longo-e-aleatorio-32+ uvicorn app.main:app --reload --port 8000

# Front → http://localhost:8080 (serve o front e repassa /api para a API, como o nginx)
python e2e/servidor.py
```

## Testes

```bash
cd backend  && pytest                                            # API (113 testes; 8 de contrato com o Appwrite real ficam pulados)
cd backend  && ruff check . && ruff format --check . && mypy app  # estilo e tipos
cd frontend && npm install && npm test                           # front (32 testes)
# roteiro no navegador (Playwright, 66 verificações): ver e2e/README.md
```

Os resultados e a rastreabilidade dos requisitos estão no [DCT](docs/dct.docx). Não há automação no GitHub: as verificações são
feitas à mão antes de cada merge.

## Publicação (Coolify)

Um único `docker-compose.yml`, igual no uso local e no Coolify. Em resumo: novo recurso do tipo Docker Compose a partir do
repositório, variáveis do `.env` em Environment Variables e três domínios com a porta interna do serviço (web → 80, api → 8000,
traefik → 80). Detalhes em [db/README.md](db/README.md#coolify).

## Estrutura

```
backend/    API FastAPI (app/api, app/core, app/repositories) + testes pytest
frontend/   App web (src/lib, src/domain, src/data, src/ui) + nginx + testes vitest
db/         Imagem do MongoDB e guia do Appwrite
e2e/        Roteiro no navegador (Playwright)
docs/       Documentação (abaixo)
docker-compose.yml   Stack completa: front + API + Appwrite
.env.example         Modelo das variáveis de ambiente
```

## Documentação

| Documento | Para quê |
| --- | --- |
| [Especificação funcional e técnica](docs/especificacao.docx) | O que o sistema faz e como é construído e publicado |
| [Manual do sistema](docs/manual.docx) | Como usar |
| [DCT — Casos de Teste](docs/dct.docx) | O que foi testado e com que resultado |
| [Anexos 8.1 a 8.6](docs/anexos.docx) | Glossário, boas práticas, commits, Git Flow, segurança e LGPD, contatos |
| [Arquitetura](docs/arquitetura.md) | Visão resumida das camadas e do fluxo |
| [db/README.md](db/README.md) | Appwrite: instalação, dados, backup e problemas comuns |
| [e2e/README.md](e2e/README.md) | Como rodar o roteiro no navegador |

## Limitações conhecidas

A integração com o Asaas é apenas a tela; o limite de tentativas de senha é guardado em memória; não há troca nem recuperação
de senha; o aceite da LGPD é exigido na tela, mas não é gravado. A lista completa, com o que fazer em cada caso, está na seção 16
da Especificação.
