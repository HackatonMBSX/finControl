FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html style.css /usr/share/nginx/html/
COPY src /usr/share/nginx/html/src
# o nginx roda como usuário 'nginx': garante leitura mesmo que os arquivos de origem tenham permissão restrita
RUN chmod -R a+rX /usr/share/nginx/html && chmod a+r /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
