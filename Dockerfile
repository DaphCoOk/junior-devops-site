FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY index.html /usr/share/nginx/html/index.html
COPY 50x.html /usr/share/nginx/html/50x.html

RUN chown -R nginx:nginx /usr/share/nginx/html/

EXPOSE 80