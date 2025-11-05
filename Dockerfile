# Użycie oficjalnego, lekkiego obrazu Nginx jako bazy (minimalny rozmiar)
FROM nginx:alpine

# Usunięcie domyślnego pliku konfiguracyjnego Nginx.
# Robimy to, aby upewnić się, że nasze pliki konfiguracyjne zostaną użyte.
RUN rm /etc/nginx/conf.d/default.conf

# Skopiowanie tymczasowego pliku konfiguracyjnego (dla Certbot Challenge) do katalogu Nginx.
# Będzie użyty przy pierwszym uruchomieniu w docker-compose.
COPY nginx.temp.conf /etc/nginx/conf.d/

# Skopiowanie docelowego, finalnego pliku konfiguracyjnego (z SSL) do katalogu Nginx.
# Będzie użyty po pomyślnym uzyskaniu certyfikatu.
COPY nginx.final.conf /etc/nginx/conf.d/

# Skopiowanie wszystkich plików projektu (HTML, CSS, JS, etc.) do głównego katalogu serwowania Nginx (webroot)
COPY . /usr/share/nginx/html/

# Ustawienie prawidłowych praw własności dla plików (użytkownik:grupa nginx),
# aby Nginx mógł je odczytywać i serwować. Jest to dobra praktyka bezpieczeństwa.
RUN chown -R nginx:nginx /usr/share/nginx/html/

# Argument używany do śledzenia wersji kompilacji. Przydatne w CI/CD do debugowania.
ARG BUILD_COMMIT_SHA="unknown"

# Zadeklarowanie portu, na którym kontener nasłuchuje (80 - HTTP)
EXPOSE 80