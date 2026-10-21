# db/ — Appwrite (banco NoSQL + autenticação)

Appwrite **2.5** self-hosted com **MongoDB**. O **DocumentsDB** (documentos JSON sem esquema) é o "banco NoSQL" do enunciado, e o
**Appwrite Auth** guarda e-mail e senha dos usuários. Os serviços ficam no `docker-compose.yml` da **raiz**, junto com a API e o
front; esta pasta só tem o que o MongoDB precisa para iniciar. Visão geral do projeto: [README da raiz](../README.md).

Todos os comandos abaixo rodam na **raiz do projeto** (a pasta do `docker-compose.yml`).

## O que tem nesta pasta

| Arquivo | Para que serve |
| --- | --- |
| `Dockerfile` | Imagem `mongo:8.2.5` com os dois scripts abaixo embutidos (o compose a usa em `build: ./db`) |
| `mongo-entrypoint.sh` | Gera o keyfile do replica set, inicializa o diretório de dados numa porta temporária (27018), cria o usuário `root` e o `appwrite`, grava o marcador `.appwrite-initialised` e entrega o comando ao entrypoint padrão do Mongo (`--replSet rs0 --auth --keyFile`) |
| `mongo-init.js` | Cria o usuário `appwrite` (senha `DB_PASSWORD`) com leitura e escrita no banco `appwrite` |

O Appwrite exige MongoDB com autenticação e replica set, por isso o entrypoint próprio. A inicialização só roda na primeira
subida: o marcador impede que ela se repita e garante que uma primeira subida interrompida seja retomada de onde parou.

## Serviços e volumes

- **Usados do Appwrite:** `traefik` (roteador interno: console em `/`, API em `/v1`), `appwrite` (API), `appwrite-console`,
  `appwrite-worker` (filas: índices, exclusão de usuários, e-mails), `appwrite-geo`, `mongodb` e `redis`.
- **Fora do compose, por não serem usados:** functions/sites (executor, orchestrator, browser), mqtt, autogravity, clickhouse
  (estatísticas de uso, desligadas com `_APP_USAGE_STATS=disabled`), realtime e tarefas de manutenção e agendamento.
- **Volumes:** `mongodb-data` (os dados), `mongodb-keyfile` (keyfile do replica set), `redis-data` e `appwrite-uploads`,
  `appwrite-cache`, `appwrite-config`, `appwrite-certificates`. Tudo que importa (dados, projeto e chave de API do Appwrite) mora neles.

## Variáveis de ambiente

Copie `.env.example` para `.env` (local) ou cole no Coolify, em Environment Variables.

| Variável | Obrigatória | Para que serve |
| --- | --- | --- |
| `JWT_SECRET` | sim | Assina o login da API (`openssl rand -hex 32`) |
| `APPWRITE_SECRET` | sim | Cifra e segredos internos do Appwrite (`openssl rand -hex 24`). **Não mude depois de criado** |
| `DB_PASSWORD` | sim | Senha do MongoDB (`openssl rand -hex 24`). O usuário só é criado na primeira inicialização: trocar depois exige recriar o volume `mongodb-data` |
| `APPWRITE_DOMAIN` | não | Domínio do console, sem `https://`. Local: `localhost`. Coolify: ex.: `db.seudominio.com` |
| `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY` | depois | Vêm do console, depois de criar o projeto e a chave (passos abaixo) |
| `APPWRITE_PORT`, `WEB_PORT`, `API_PORT` | não | Portas locais do console, do app e da API (padrão 8081, 8090, 8091). Só em `127.0.0.1` |

Ajustes do Appwrite que importam para o banco, já definidos em `x-appwrite-env` no compose:

- `_APP_DOCUMENTSDB: enabled` — **obrigatório.** No Appwrite 2.5 o DocumentsDB vem desligado por padrão, e isso vale até para
  chave de API: sem esta variável a API recebe 403 "service disabled" e o banco nunca é criado.
- `_APP_DB_ADAPTER: mongodb` e `_APP_DB_ADAPTER_DOCUMENTSDB: mongodb` — MongoDB para tudo.
- `_APP_CONSOLE_WHITELIST_ROOT: enabled` — só o primeiro cadastro no console vira administrador; depois o cadastro fecha.
- `_APP_OPTIONS_FORCE_HTTPS: disabled` — o HTTPS é do proxy do Coolify.

## Primeira vez (local)

```bash
cp .env.example .env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -hex 32)|;s|^APPWRITE_SECRET=.*|APPWRITE_SECRET=$(openssl rand -hex 24)|;s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 24)|" .env
docker compose up -d --build        # o Appwrite leva 1–2 min para ficar saudável; a API só inicia depois
```

1. Abra http://localhost:8081, crie sua conta de administrador e um projeto (ex.: **fincontrol**). **Espere o console terminar
   de criar o projeto** antes de sair da tela (veja "Problemas comuns", o caso do projeto incompleto).
2. Copie o **Project ID** (Configurações do projeto).
3. *Integrações → Chaves de API → Criar*: escopos de **Databases, Collections, Documents e Indexes** e de **Users e Sessions**
   (leitura e escrita). Copie a chave.
4. No `.env`, preencha `APPWRITE_PROJECT_ID` e `APPWRITE_API_KEY` e rode `docker compose up -d api`.
5. Confira que o banco está pronto:

```bash
docker compose ps                                        # todos healthy
docker compose exec appwrite printenv _APP_DOCUMENTSDB   # enabled
docker compose logs api | grep -i "banco preparado"      # a API criou o banco e as coleções
curl -s http://localhost:8091/ready                      # {"status":"ready"}
```

O app fica em http://localhost:8090 e a API (a raiz abre o Swagger) em http://localhost:8091.

## Estrutura dos dados

A API cria sozinha o banco **`fincontrol`** e as coleções: na subida (`warm_up`, em segundo plano, com novas tentativas se o
Appwrite ainda estiver lento) e sob demanda, no primeiro uso de cada uma. Não há esquema de campos a declarar.

- Toda coleção nasce com permissões vazias: só a **chave de API da API** acessa o banco; o navegador nunca fala com o Appwrite.
- Todo documento tem `id`, `familyId`, `createdAt` e `updatedAt`. O `familyId` é o que isola uma família da outra: toda leitura
  e escrita da API filtra por ele. Cada coleção tem o índice `idx_family` sobre `familyId`.

| Coleção | O que guarda | Campos principais |
| --- | --- | --- |
| `familias` | Uma por família (`familyId` fixo `_root`) | `nome` |
| `perfis` | Usuários da família. O `id` é o mesmo do usuário no Appwrite Auth | `userId`, `nome`, `email`, `papel` (`admin`, `membro` ou `leitor`) |
| `despesas` | Lançamentos | `descricao`, `valor`, `competencia` (AAAA-MM), `status` (`ABERTO` ou `PAGO`), `vencimento`, `pagoEm`, `categoria`, `tipo`, `banco`, `centro`, `grupo`, `transacao`, `dtpg`, `recorrente`, `origemId` |
| `categorias` | Cadastro auxiliar | `nome`, `cor`, `meta` |
| `tipos` | Cadastro auxiliar | `nome`, `cor`, `desc` |
| `bancos` | Cadastro auxiliar | `nome`, `ativo` |
| `centros` | Cadastro auxiliar (centros de custo) | `nome` |
| `configuracoes` | Um documento por família, de id `config_<familyId>` | `orcamento`, `renda`, `familia`, `fechamento`, `alertaPct`, `reservaMeta`, `somAtivo` |
| `integracoes` | Um documento por família, de id `asaas_<familyId>` | `conectado`, `ambiente`, `apiKeyCifrada` (a chave do Asaas, cifrada) |
| `backups` | Histórico de backups da família (os 10 últimos). Criada na primeira exportação | `motivo`, `por`, `geradoEm`, `contagens`, `checksum`, `conteudo` (o arquivo em JSON) |
| `healthcheck` | Documento de teste criado e apagado pelo `/ready` | `familyId` |

**Autenticação.** O e-mail e a senha ficam no **Appwrite Auth** (o Appwrite guarda o hash). A API cria o usuário com a chave de
servidor. No login, abre uma sessão no Appwrite só para validar a senha e a apaga em seguida: quem identifica o usuário nas
chamadas seguintes é o JWT da própria API. O Appwrite também limita as tentativas de login (responde 429).

## Ver os dados

Nesta versão self-hosted o console do Appwrite **não mostra o DocumentsDB**. Para ver as coleções e os documentos, use a API REST
do Appwrite com a chave do `.env`:

```bash
. ./.env        # carrega APPWRITE_PROJECT_ID e APPWRITE_API_KEY
curl -s http://localhost:8081/v1/documentsdb/fincontrol/collections \
  -H "X-Appwrite-Project: $APPWRITE_PROJECT_ID" -H "X-Appwrite-Key: $APPWRITE_API_KEY" | python3 -m json.tool

curl -s http://localhost:8081/v1/documentsdb/fincontrol/collections/despesas/documents \
  -H "X-Appwrite-Project: $APPWRITE_PROJECT_ID" -H "X-Appwrite-Key: $APPWRITE_API_KEY" | python3 -m json.tool
```

A listagem de documentos traz 25 por página. O console continua útil para os **usuários** (Auth) e para as chaves de API.

## Backup e recuperação

- **Por família:** a API exporta e restaura os dados da família em JSON (`/api/v1/backup`, só administrador), com checksum e um
  histórico dos 10 últimos.
- **Do servidor inteiro:** são os volumes do Docker (veja "Serviços e volumes"). O essencial é o `mongodb-data`, que guarda os
  dados, o projeto e as chaves do Appwrite. Guarde também o `.env`: sem o `APPWRITE_SECRET`, os campos cifrados do Appwrite
  deixam de abrir.
- **Zerar tudo (local):** `docker compose down -v` apaga os volumes, inclusive o projeto e a chave de API do Appwrite. Depois,
  repita a "Primeira vez" a partir do passo 1.

## Problemas comuns

| Sintoma | Causa provável | O que fazer |
| --- | --- | --- |
| `docker compose up` para pedindo `JWT_SECRET`, `APPWRITE_SECRET` ou `DB_PASSWORD` | `.env` sem um dos três segredos | Preencher o `.env` (veja "Primeira vez") |
| A API responde 403 "service disabled" e o log nunca mostra "banco preparado" | `_APP_DOCUMENTSDB` não está `enabled` no `appwrite` e no `appwrite-worker` | Conferir o compose e rodar `docker compose up -d`. O `restart` não relê o compose |
| Cadastro responde `internal_error` e o log do Appwrite (`docker compose logs appwrite`) mostra `Collection not found` (ex.: `targets`) | Projeto criado de forma incompleta: a criação das coleções internas do projeto foi interrompida | Criar **outro projeto** no console, gerar uma nova chave, atualizar `APPWRITE_PROJECT_ID` e `APPWRITE_API_KEY` no `.env` e rodar `docker compose up -d api` |
| `appwrite` aparece `unhealthy` nos primeiros minutos | Normal: o Mongo inicia o replica set (até 60 s) e o Appwrite tem 120 s de carência | Esperar 1–2 min e rodar `docker compose ps` de novo |
| O Mongo recusa a conexão depois de trocar `DB_PASSWORD` | O volume `mongodb-data` guarda a senha antiga | Voltar a senha antiga ou recriar os volumes (`docker compose down -v`) |
| A API não sobe em produção com erro sobre `JWT_SECRET` | Em `APP_ENV=production` o segredo precisa ter 32 caracteres ou mais | Gerar com `openssl rand -hex 32` |
| Porta 8081, 8090 ou 8091 ocupada | Outro programa usa a porta | Mudar `APPWRITE_PORT`, `WEB_PORT` ou `API_PORT` no `.env` |

## Coolify

1. Novo recurso → repositório do GitHub → build pack **Docker Compose** (arquivo `docker-compose.yml`).
2. Em Environment Variables, colar o `.env`: os 3 segredos, `APP_ENV=production` e `APPWRITE_DOMAIN` (domínio do console, sem `https://`).
3. Domínios, sempre com a **porta interna** do serviço:
   - **web** → `https://app.seudominio.com:80` (o app);
   - **api** → `https://api.seudominio.com:8000` (a API; o Swagger abre na raiz e fica em `/docs`);
   - **traefik** → `https://db.seudominio.com:80`, o mesmo valor de `APPWRITE_DOMAIN` (console do Appwrite).
4. Deploy. Acesse o console, crie o projeto e a chave de API como na "Primeira vez", preencha `APPWRITE_PROJECT_ID` e
   `APPWRITE_API_KEY` e faça **Redeploy**.

As portas publicadas no compose (8090, 8091 e 8081) ficam só em `127.0.0.1` e usam números que o Coolify não ocupa na VPS (ele
usa 80, 443, 8000 e 8080); servem ao uso local e não expõem nada lá, onde o acesso é pelos domínios.
