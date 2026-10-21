# Arquitetura

Visão resumida. O texto completo (rotas, dados, segurança, implantação) está na Parte B da
[Especificação](especificacao.docx).

## Visão geral

O navegador só conversa com o **nginx**, que entrega o front e repassa `/api/` para a **API**. Só a API fala com o **Appwrite**.
O navegador nunca acessa o banco.

```
   navegador (HTML + CSS + JS, módulos ES)
        |  HTTPS (Coolify / Traefik)
        v
+----------------------------------------------------------+
| web — nginx 1.27                                         |
|   /      arquivos estáticos e cabeçalhos de segurança    |
|   /api/  proxy para api:8000 (mesma origem, sem CORS)    |
+----------------------------------------------------------+
                              v
+----------------------------------------------------------+
| api — FastAPI, Python 3.13                               |
|   rotas -> núcleo -> repositório                         |
|   JWT, permissões, validação, backup, logs em JSON       |
+----------------------------------------------------------+
                              v   REST + chave de API
+----------------------------------------------------------+
| Appwrite 2.5.0 — Auth + DocumentsDB                      |
|   traefik · appwrite · console · worker · geo            |
|   mongodb (replica set) · redis                          |
+----------------------------------------------------------+
```

## Camadas da API (`backend/app`)

| Camada | Pasta | Responsabilidade |
| --- | --- | --- |
| Rotas | `api/` | Recebem o pedido, validam (Pydantic), checam o papel e chamam o repositório |
| Núcleo | `core/` | Configurações, erros padronizados, logs em JSON, senhas e tokens, cifra de segredos |
| Repositório | `repositories/` | Interface `Repository` com duas implementações: memória (testes) e Appwrite (produção) |
| Login | `auth_provider.py` | Provedor de login: memória ou Appwrite Auth |

## Camadas do front (`frontend/src`)

`lib` (cliente HTTP, formatação) → `domain` (regras puras) → `data` (estado e serviços que chamam a API) → `ui` (telas e eventos).
Uma camada só importa as de baixo.

## Fluxo de um pedido

1. O front envia `Authorization: Bearer <token>` para `/api/v1/...`.
2. O nginx repassa à API; o middleware cria o `X-Request-ID`.
3. `current_user` valida o JWT e entrega usuário, família e papel; `require_roles` confere a permissão.
4. O repositório lê ou grava **sempre filtrando pelo `familyId` do token**.
5. A resposta volta sem o `familyId`; erros saem no formato `{"error": {code, message, requestId, details}}`.

## Implantação

Um único `docker-compose.yml` com nove serviços: `web`, `api`, `traefik`, `appwrite`, `appwrite-console`, `appwrite-worker`,
`appwrite-geo`, `mongodb` e `redis`. Portas locais só em `127.0.0.1` (app 8090, API 8091, console 8081). No Coolify, o acesso é
por domínios: web → 80, api → 8000, traefik → 80. Guia completo em [../db/README.md](../db/README.md).
