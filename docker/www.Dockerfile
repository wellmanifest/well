# syntax=docker/dockerfile:1.7
FROM nginx:1.27.5-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY www /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=10 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
