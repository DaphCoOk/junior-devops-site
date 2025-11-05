FROM nginx:alpine


RUN rm /etc/nginx/conf.d/default.conf

# Nginx ищет в /etc/nginx/conf.d/. Мы используем default.conf,

COPY nginx.temp.conf /etc/nginx/conf.d/
COPY nginx.final.conf /etc/nginx/conf.d/

COPY . /usr/share/nginx/html/

RUN chown -R nginx:nginx /usr/share/nginx/html/

ARG BUILD_COMMIT_SHA="unknown"


EXPOSE 80