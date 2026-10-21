# Roteiro de ponta a ponta (navegador)

Percorre o sistema como uma pessoa: cadastro da família, login, despesas, meses, Gerar mês, abas, backup e restauração, papéis
(leitor), exclusão de conta e de família. Também confere a tela em largura de celular e de computador (cabeçalho sem
sobreposição em 320, 360 e 420 px, calendário de mês, rolagem preservada, alertas pulsantes por aparelho).

São **66 verificações**. Usa Playwright (Python) e uma API em memória, sem Docker nem Appwrite; por isso os dados somem ao
reiniciar a API e é preciso reiniciá-la antes de repetir o roteiro.

```bash
pip install playwright && playwright install chromium        # uma vez
cd backend
REPOSITORY_BACKEND=memory JWT_SECRET=troque-por-um-valor-longo-e-aleatorio-32+ uvicorn app.main:app --port 8000 &
python ../e2e/servidor.py &                                  # front em http://127.0.0.1:8080, repassando /api para a API
python ../e2e/roteiro.py                                     # reinicie a API antes de repetir
```

`servidor.py` imita o nginx da publicação: entrega o front e repassa `/api/*` para `http://127.0.0.1:8000`. Serve também para
abrir o app à mão durante o desenvolvimento.

O roteiro termina com código 0 quando não há falhas e grava `docs/e2e-resultado.json` (data da execução, número de verificações e
de falhas). O [DCT](../docs/dct.docx) usa os casos `OK`/`FAIL` desta execução como resultado dos casos de tela; o arquivo é só
o registro da última rodada.

O que o roteiro **não** cobre: o Appwrite real, o som audível, a publicação no Coolify e um celular de verdade. Esses itens
aparecem no DCT como casos manuais ou pendentes.
