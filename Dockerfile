FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.temp.conf /usr/share/nginx/html/
COPY nginx.final.conf /usr/share/nginx/html/

COPY . /usr/share/nginx/html/

RUN chown -R nginx:nginx /usr/share/nginx/html/

ARG BUILD_DATE
ARG BUILD_ID

RUN sed -i "s|\\$\\$BUILD_DATE\\$\\$|$BUILD_DATE|g" /usr/share/nginx/html/index.html
RUN sed -i "s|\\$\\$BUILD_ID\\$\\$|$BUILD_ID|g" /usr/share/nginx/html/index.html

EXPOSE 80