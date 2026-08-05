# syntax=docker/dockerfile:1.7
FROM nginx:1.27.5-alpine
COPY examples/iot-three-layer/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY examples/iot-three-layer/frontend/index.html /usr/share/nginx/html/index.html
COPY examples/iot-three-layer/frontend/app.js /usr/share/nginx/html/app.js
EXPOSE 8080
