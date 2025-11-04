FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.temp.conf /usr/share/nginx/html/
COPY nginx.final.conf /usr/share/nginx/html/

COPY . /usr/share/nginx/html/

RUN chown -R nginx:nginx /usr/share/nginx/html/

ARG BUILD_COMMIT_SHA="unknown"

RUN sed -i "s#BUILD_DATE_PLCH#$BUILD_COMMIT_SHA#g" /usr/share/nginx/html/index.html
RUN sed -i "s#BUILD_ID_PLCH#$BUILD_COMMIT_SHA#g" /usr/share/nginx/html/index.html

EXPOSE 80