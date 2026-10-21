# syntax=docker/dockerfile:1
# Receita da imagem Docker da API.
# Usa dois estágios: o primeiro instala as dependências e o segundo copia só o resultado e o código,
# o que deixa a imagem final menor. A API roda com um usuário sem privilégios de administrador.
# Usado pelo docker-compose.yml e pelo deploy (Coolify).

# Estágio 1: imagem com Python para instalar as dependências.
FROM python:3.13-slim AS build
# Pasta de trabalho temporária deste estágio.
WORKDIR /w
# Copia só a lista de dependências, para aproveitar o cache quando o código muda.
COPY requirements.txt .
# Instala as dependências numa pasta separada, que será copiada para a imagem final.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Estágio 2: imagem final, só com o necessário para rodar.
FROM python:3.13-slim
# Logs saem na hora, sem arquivos .pyc, e a porta padrão é 8000.
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8000
# Cria o usuário sem privilégios que vai rodar a API.
RUN useradd --create-home --uid 10001 app
# Pasta onde fica o código da aplicação.
WORKDIR /app
# Traz as dependências instaladas no estágio 1.
COPY --from=build /install /usr/local
# Copia o código da API (os testes ficam de fora).
COPY app ./app
# Deixa os arquivos legíveis por qualquer usuário, inclusive o usuário app.
RUN chmod -R a+rX /app
# A partir daqui tudo roda como o usuário sem privilégios.
USER app
# Informa a porta em que a API escuta.
EXPOSE 8000
# A cada 30 s chama /health; se falhar 3 vezes seguidas, o contêiner é marcado como doente.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health',timeout=2)" || exit 1
# Sobe a API com o uvicorn na porta PORT, confiando nos cabeçalhos do proxy reverso.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
