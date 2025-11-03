FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.temp.conf /usr/share/nginx/html/
COPY nginx.final.conf /usr/share/nginx/html/

COPY . /usr/share/nginx/html/

RUN chown -R nginx:nginx /usr/share/nginx/html/

EXPOSE 80