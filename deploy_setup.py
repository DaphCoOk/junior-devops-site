import paramiko
import time
import os
import sys

#  KONFIGURACJA SERWERA I DOSTĘPU 
VPS_HOST = '46.62.147.93'          # Adres IP nowej maszyny wirtualnej
VPS_USER = 'root'                  # Użytkownik administratora (root)
# Ścieżka do PRYWATNEGO klucza SSH (BEZ .pub)
PRIVATE_KEY_PATH = r'C:\Users\karlo\.ssh\final_deploy_key'

#  KONFIGURACJE PROJEKTU I ŚRODOWISKA 
DOMAIN = 'TestUst.freeddns.org'    # Docelowa nazwa domeny dla Certbot
REPO_URL = 'https://github.com/DaphCoOk/junior-devops-site' # URL projektu na GitHub
# Ścieżka do  PUBLICZNEGO klucza SSH (Z .pub)
PUBLIC_KEY_CONTENT_PATH = r'C:\Users\karlo\.ssh\final_deploy_key.pub'
# EMAIL: Wymagany przez Certbot
CERTBOT_EMAIL = "deployer@test.com"

#  ZMIENNE POMOCNICZE DLA LOGIKI PODMIANY PLIKÓW 
WEB_SERVICE_NAME = "web"
TARGET_CONFIG_NAME = "default.conf"
NGINX_HOST_DIR = "/app/repo/nginx"
# -

#  KROK 0: ZAŁADOWANIE PUBLICZNEGO KLUCZA LOKALNIE 
try:
    with open(PUBLIC_KEY_CONTENT_PATH, 'r') as f:
        zawartosc_klucza_publicznego = f.read().strip()
except FileNotFoundError:
    print(f"[KRYTYCZNA OSTRZEŻENIE] Nie znaleziono klucza publicznego pod ścieżką: {PUBLIC_KEY_CONTENT_PATH}")
    print("Upewnij się, że plik 'final_deploy_key.pub' istnieje. Próba użycia pustego klucza.")
    zawartosc_klucza_publicznego = ""

#  BLOK BASH 1: PROVISIONING I BEZPIECZEŃSTWO 
KOMENDA_PROVISIONING_BASH = f"""
    echo ' 1. Aktualizacja systemu i instalacja narzędzi (git, curl, docker-compose) '
    sudo apt update
    sudo apt install -y git python3-pip curl build-essential docker-compose-plugin ca-certificates

    echo ' 2. Instalacja platformy Docker. '
    # Dodanie klucza i repozytorium Dockera
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    # Instalacja
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo ' 3. Tworzenie użytkownika 'deployer' i nadawanie mu praw Docker. '
    sudo useradd -m -s /bin/bash deployer || true
    sudo usermod -aG docker deployer

    echo ' 4. Konfiguracja SSH-dostępu dla użytkownika 'deployer'. '
    USER_SSH_DIR="/home/deployer/.ssh"
    AUTH_KEYS="$USER_SSH_DIR/authorized_keys"

    sudo mkdir -p $USER_SSH_DIR

    if [ -n "{zawartosc_klucza_publicznego}" ] && ! sudo grep -q -F "{zawartosc_klucza_publicznego}" $AUTH_KEYS; then
        echo "Dodawanie publicznego klucza do $AUTH_KEYS"
        echo "{zawartosc_klucza_publicznego}" | sudo tee -a $AUTH_KEYS
    else
        echo "Klucz publiczny jest już ustawiony lub nie został podany. Pomijanie dodawania."
    fi

    # Ustawienie praw dostępu (zawsze)
    sudo chown -R deployer:deployer $USER_SSH_DIR
    sudo chmod 700 $USER_SSH_DIR
    sudo chmod 600 $AUTH_KEYS
"""

#  BLOK BASH 2: WDROŻENIE (Klonowanie, Podmiana Konfigów, Certbot, Uruchomienie SSL) 
KOMENDA_WDROZENIA_CERTBOT = f"""
    # 0. KONFIGURACJA FIREWALL UFW (Porty 80, 443)
    echo ' 0. UFW: Otwieranie portów '
    sudo apt install -y ufw
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable || true
    sudo ufw status verbose

    # 1. Klonowanie/Aktualizacja projektu
    sudo mkdir -p /app/repo
    sudo git clone {REPO_URL} /app/repo || (cd /app/repo && sudo git pull origin main)
    sudo chown -R deployer:deployer /app/repo
    
    # 2. Wymuś bezpieczny katalog git (dla deployer)
    sudo su - deployer -c "git config --global --add safe.directory /app/repo"

    # 3. Przygotowanie katalogów dla Certbota
    CERTBOT_WEBROOT_DIR="/app/repo/data/certbot/www"
    sudo mkdir -p $CERTBOT_WEBROOT_DIR
    sudo chown -R deployer:deployer /app/repo/data
    
    #  LOGIKA CERTYFIKATU Z PODMIANĄ NGINX (wykonywana jako deployer) 
    sudo su - deployer -c "
        NGINX_HOST_DIR='{NGINX_HOST_DIR}'
        TARGET_CONFIG_NAME='{TARGET_CONFIG_NAME}'
        DOMAIN='{DOMAIN}'
        CERTBOT_EMAIL='{CERTBOT_EMAIL}'
        
        # KROK 0: Czyszczenie starych usług
        echo ' 3.1. Czyszczenie starych usług '
        cd /app/repo && docker compose down --remove-orphans
        docker ps -a -q --filter name=certbot | xargs -r docker rm -f
        
        CERT_FILE=\"/app/repo/data/certbot/conf/live/\$DOMAIN/fullchain.pem\"

        # 4. Czy certyfikat istnieje?
        if [ ! -f \"\$CERT_FILE\" ]; then
            echo 'Brak certyfikatów SSL. Startuję tymczasowy Nginx (HTTP) dla Certbot.'
            
            # KROK 4.1: KOPIUJEMY TYMCZASOWY KONFIG (HTTP only)
            cp \$NGINX_HOST_DIR/nginx.temp.conf \$NGINX_HOST_DIR/\$TARGET_CONFIG_NAME
            
            # KROK 4.2: Startujemy TYLKO kontener web (na porcie 80)
            echo 'Uruchamiam web...'
            cd /app/repo && docker compose up -d web
            
            # KROK 4.3: Oczekujemy na Nginx
            echo 'Oczekuję na odpowiedź Nginx (port 80)...'
            sleep 5 # Krótka pauza na start kontenera
            
            # KROK 4.4: Uruchamiamy Certbot po certyfikat
            echo 'Startuję Certbot...'
            docker compose run --rm certbot certonly \\
                --webroot -w /var/www/certbot \\
                -d \"\$DOMAIN\" -d \"www.\$DOMAIN\" \\
                --email \$CERTBOT_EMAIL \\
                --rsa-key-size 4096 \\
                --agree-tos \\
                --no-eff-email

            # Zatrzymujemy tymczasowy Nginx niezależnie od wyniku Certbot
            echo 'Zatrzymuję tymczasowy Nginx...'
            docker compose down

        else
            echo 'Certyfikaty SSL już istnieją. Pomijam pobieranie.'
        fi

        # 5. KROK KOŃCOWY: Kopiujemy końcowy konfig (SSL) i startujemy cały stos.
        echo ' 5. Aktywacja konfiguracji SSL i uruchomienie całego stosu '
        
        # KROK 5.1: KOPIUJEMY KOŃCOWY KONFIG (SSL)
        cp \$NGINX_HOST_DIR/nginx.final.conf \$NGINX_HOST_DIR/\$TARGET_CONFIG_NAME
        
        # KROK 5.2: Uruchamiamy usługi (web i certbot-renew)
        echo 'Startuję końcowy stos (SSL)...'
        cd /app/repo && docker compose up -d
        
        echo ' Wdrożenie zakończone. '
    "
    
    # 6. Sprawdzenie statusu kontenerów.
    sudo docker ps
"""

#  FUNKCJE PARAMIKO (Tłumaczenie na PL) 

def wykonaj_zdalne_polecenie_pty(polaczenie_ssh, komenda, nazwa_kroku="Komenda"):
    """Wykonuje polecenie Bash na zdalnym serwerze, używając PTY."""
    print(f"\n[START] Rozpoczynam krok: {nazwa_kroku}")
    # print(f"Komenda:\n{komenda.strip()}") # Opcjonalne: wyświetlanie polecenia

    transport = polaczenie_ssh.get_transport()
    if not transport:
        print("[KRYTYCZNY BŁĄD] Brak transportu SSH.")
        return False

    channel = transport.open_session()
    channel.get_pty()  # Wymagane, aby komendy sudo działały poprawnie
    channel.exec_command(komenda)

    output = ""
    error = ""
    # Czytanie wyjścia w czasie rzeczywistym
    while not channel.exit_status_ready():
        if channel.recv_ready():
            output += channel.recv(1024).decode('utf-8', errors='replace')
        if channel.recv_stderr_ready():
            error += channel.recv_stderr(1024).decode('utf-8', errors='replace')
        time.sleep(0.1)

    # Doładowanie pozostałych danych
    output += channel.recv(1024).decode('utf-8', errors='replace')
    error += channel.recv_stderr(1024).decode('utf-8', errors='replace')

    exit_status = channel.recv_exit_status()
    channel.close()

    print(" Rezultat ")
    if output:
        print(output.strip())

    if exit_status != 0:
        if error:
            print(f" BŁĄD (Kod wyjścia: {exit_status}) \n{error.strip()}")
        # W przypadku błędu w Certbot, nie przerywamy, ponieważ Nginx i tak powinien wystartować (bez SSL)
        if "certonly" in komenda:
            print(f"[OSTRZEŻENIE] Krok Certbot zakończony z błędem (Kod: {exit_status}). Kontynuuję wdrożenie.")
            return True
        print(f"[BŁĄD KRYTYCZNY] Krok '{nazwa_kroku}' zakończył się niepowodzeniem.")
        sys.exit(1) # Przerywamy skrypt w przypadku poważnych błędów
        
    print(f"[SUKCES] Krok '{nazwa_kroku}' zakończony.")
    return True

def automatyzacja_wdrozenia():
    """Główna funkcja logiki automatycznego Provisioning'u."""

    #  KROK 0: SPRAWDZENIE ZAŁADOWANIA KLUCZA PUBLICZNEGO 
    if not zawartosc_klucza_publicznego and "deployer" in KOMENDA_PROVISIONING_BASH:
        print("[OSTRZEŻENIE] Nie udało się załadować klucza publicznego. Upewnij się, że klucz 'root' jest ustawiony!")
        
    polaczenie_ssh = paramiko.SSHClient()
    polaczenie_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Próba SSH-połączenia
        polaczenie_ssh.connect(hostname=VPS_HOST, username=VPS_USER, key_filename=PRIVATE_KEY_PATH, timeout=15)
        print(f"[SUKCES] Nawiązano połączenie z VPS: {VPS_HOST}")

        # ETAP 1: PROVISIONING
        print("\n ETAP 1: Provisioning i Konfiguracja Użytkownika Deployer ")
        wykonaj_zdalne_polecenie_pty(polaczenie_ssh, KOMENDA_PROVISIONING_BASH, "Provisioning systemu i instalacja Docker")

        # ETAP 2: DEPLOYMENT (Klonowanie, Fix UFW, Podmiana Konfigów, Uruchomienie)
        print("\n ETAP 2: Wdrożenie Projektu, Konfiguracja UFW i Logika Certyfikatów SSL ")
        wykonaj_zdalne_polecenie_pty(polaczenie_ssh, KOMENDA_WDROZENIA_CERTBOT, "Deployment projektu i start Docker Compose")

        print("\n\n AUTOMATYCZNE WDROŻENIE ZAKOŃCZONE ")
        print(f"Usługa powinna być teraz dostępna pod adresem: https://{DOMAIN}")
        print("Instancja VPS jest w pełni gotowa do otrzymywania aktualizacji.")

    except paramiko.AuthenticationException:
        print("[BŁĄD AUTENTYKACJI] Sprawdź, czy klucz PRYWATNY jest poprawny i ma odpowiednie uprawnienia dostępu.")
    except Exception as e:
        print(f"[KRYTYCZNY BŁĄD] Wystąpił nieoczekiwany błąd: {e}")
    finally:
        polaczenie_ssh.close()

if __name__ == "__main__":
    # Sprawdzenie i instalacja biblioteki Paramiko
    try:
        import paramiko
    except ImportError:
        print("Instaluję bibliotekę 'paramiko'...")
        os.system(f'{sys.executable} -m pip install paramiko') # Używamy sys.executable dla pewności
        
    print("Rozpoczęcie automatycznego Provisioning'u serwera...")
    automatyzacja_wdrozenia()