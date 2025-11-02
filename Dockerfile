Используем базовый образ Nginx
FROM nginx:alpine

Удаляем конфигурацию Nginx по умолчанию
RUN rm /etc/nginx/conf.d/default.conf

Копируем наш файл index.html в директорию Nginx
Предполагая, что index.html лежит в корне вашего репозитория
COPY index.html /usr/share/nginx/html/index.html

Порт, который будет слушать Nginx
EXPOSE 80