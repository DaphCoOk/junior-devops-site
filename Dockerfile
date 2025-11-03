...
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.temp.conf /etc/nginx/conf.d/nginx.temp.conf
COPY nginx.final.conf /etc/nginx/conf.d/nginx.final.conf

COPY . /usr/share/nginx/html/

RUN chown -R nginx:nginx /usr/share/nginx/html/
...