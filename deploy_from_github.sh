#!/bin/bash

# Skrypt do wdrożenia aplikacji na serwer produkcyjny dict.c11.net.pl
# wykorzystując repozytorium GitHub
# Uruchom ten skrypt lokalnie

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Konfiguracja
SERVER="marek@dict.c11.net.pl"
REMOTE_DIR="kindle_dict"
GITHUB_REPO="https://github.com/MarekWo/kindle_dict.git"

echo -e "${GREEN}Rozpoczynam wdrażanie aplikacji na serwer produkcyjny z GitHub...${NC}"

# Tworzenie skryptu instalacyjnego na serwerze
echo -e "${YELLOW}Tworzenie skryptu instalacyjnego na serwerze...${NC}"

ssh $SERVER "cat > ~/deploy_kindle_dict.sh << 'EOL'
#!/bin/bash

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Konfiguracja
GITHUB_REPO=\"https://github.com/MarekWo/kindle_dict.git\"
APP_DIR=\"kindle_dict\"

echo -e \"\${GREEN}Rozpoczynam wdrażanie aplikacji Kindle Dictionary Creator...\${NC}\"

# Aktualizacja systemu
echo -e \"\${YELLOW}Aktualizacja systemu...\${NC}\"
sudo apt-get update
sudo apt-get upgrade -y

# Instalacja Dockera
echo -e \"\${YELLOW}Instalacja Dockera...\${NC}\"
if ! command -v docker &> /dev/null; then
    echo -e \"\${YELLOW}Docker nie jest zainstalowany. Instaluję...\${NC}\"
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository \"deb [arch=amd64] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable\"
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker \$USER
    echo -e \"\${GREEN}Docker został zainstalowany.\${NC}\"
else
    echo -e \"\${GREEN}Docker jest już zainstalowany.\${NC}\"
fi

# Instalacja Docker Compose
echo -e \"\${YELLOW}Instalacja Docker Compose...\${NC}\"
if ! command -v docker-compose &> /dev/null; then
    echo -e \"\${YELLOW}Docker Compose nie jest zainstalowany. Instaluję...\${NC}\"
    sudo curl -L \"https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e \"\${GREEN}Docker Compose został zainstalowany.\${NC}\"
else
    echo -e \"\${GREEN}Docker Compose jest już zainstalowany.\${NC}\"
fi

# Instalacja Git
echo -e \"\${YELLOW}Instalacja Git...\${NC}\"
if ! command -v git &> /dev/null; then
    echo -e \"\${YELLOW}Git nie jest zainstalowany. Instaluję...\${NC}\"
    sudo apt-get install -y git
    echo -e \"\${GREEN}Git został zainstalowany.\${NC}\"
else
    echo -e \"\${GREEN}Git jest już zainstalowany.\${NC}\"
fi

# Klonowanie lub aktualizacja repozytorium
if [ -d \"\${APP_DIR}/.git\" ]; then
    echo -e \"\${YELLOW}Aktualizacja repozytorium...\${NC}\"
    cd \"\${APP_DIR}\"
    git pull
else
    echo -e \"\${YELLOW}Klonowanie repozytorium...\${NC}\"
    git clone \"\${GITHUB_REPO}\" \"\${APP_DIR}\"
fi

# Tworzenie katalogów dla projektu
echo -e \"\${YELLOW}Tworzenie katalogów dla projektu...\${NC}\"
mkdir -p \"\${APP_DIR}/logs\" \"\${APP_DIR}/nginx/ssl\"

# Kopiowanie certyfikatów SSL
echo -e \"\${YELLOW}Kopiowanie certyfikatów SSL...\${NC}\"
# Domyślna ścieżka dla certyfikatów Let's Encrypt, można dostosować
SSL_CERT_PATH=\"\${SSL_CERT_PATH:-\$HOME/ssl/config/live/dict.c11.net.pl}\"
echo -e \"\${YELLOW}Używam ścieżki do certyfikatów: \${SSL_CERT_PATH}\${NC}\"
cp \"\${SSL_CERT_PATH}/fullchain.pem\" \"\${APP_DIR}/nginx/ssl/\"
cp \"\${SSL_CERT_PATH}/privkey.pem\" \"\${APP_DIR}/nginx/ssl/\"
chmod 644 \"\${APP_DIR}/nginx/ssl/\"*.pem

# Generowanie bezpiecznego klucza dla Django
echo -e \"\${YELLOW}Generowanie bezpiecznego klucza dla Django...\${NC}\"
DJANGO_SECRET_KEY=\$(openssl rand -base64 50 | tr -dc 'a-zA-Z0-9!@#$%^&*(-_=+)' | head -c50)

# Tworzenie pliku .env jeśli nie istnieje
if [ ! -f \"\${APP_DIR}/.env\" ]; then
    echo -e \"\${YELLOW}Tworzenie pliku .env...\${NC}\"
    cp \"\${APP_DIR}/.env.example\" \"\${APP_DIR}/.env\"
    # Aktualizacja zmiennych środowiskowych
    sed -i \"s/DEBUG=True/DEBUG=False/\" \"\${APP_DIR}/.env\"
    sed -i \"s/SECRET_KEY=your_secret_key_here/SECRET_KEY=\${DJANGO_SECRET_KEY}/\" \"\${APP_DIR}/.env\"
    sed -i \"s/ALLOWED_HOSTS=localhost,127.0.0.1/ALLOWED_HOSTS=dict.c11.net.pl,localhost,127.0.0.1/\" \"\${APP_DIR}/.env\"
    echo -e \"\${GREEN}Plik .env został utworzony.\${NC}\"
    echo -e \"\${RED}WAŻNE: Musisz zaktualizować hasło bazy danych w pliku .env przed uruchomieniem kontenerów!\${NC}\"
    echo -e \"\${RED}Jeśli tego nie zrobisz, baza danych nie uruchomi się poprawnie.\${NC}\"
    echo -e \"\${YELLOW}nano \${APP_DIR}/.env\${NC}\"
else
    echo -e \"\${GREEN}Plik .env już istnieje.\${NC}\"
fi

echo -e \"\${GREEN}Konfiguracja środowiska produkcyjnego zakończona.\${NC}\"
echo -e \"\${RED}WAŻNE: Przed uruchomieniem aplikacji, upewnij się, że zaktualizowałeś plik .env!\${NC}\"
echo -e \"\${GREEN}Aby uruchomić aplikację, wykonaj:\${NC}\"
echo -e \"\${YELLOW}cd \${APP_DIR}\${NC}\"
echo -e \"\${YELLOW}docker-compose -f docker-compose.prod.yml up -d\${NC}\"

echo -e \"\${YELLOW}Aby wykonać migracje bazy danych, wykonaj:\${NC}\"
echo -e \"\${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py migrate\${NC}\"

echo -e \"\${YELLOW}Aby zebrać pliki statyczne, wykonaj:\${NC}\"
echo -e \"\${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput --settings=kindle_dict.settings.prod\${NC}\"

echo -e \"\${YELLOW}Aby utworzyć superużytkownika, wykonaj:\${NC}\"
echo -e \"\${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser\${NC}\"
EOL"

# Nadanie uprawnień do wykonania skryptu
ssh $SERVER "chmod +x ~/deploy_kindle_dict.sh"

echo -e "${GREEN}Skrypt instalacyjny został utworzony na serwerze.${NC}"
echo -e "${YELLOW}Aby dokończyć wdrażanie, zaloguj się na serwer i uruchom:${NC}"
echo -e "${YELLOW}ssh $SERVER${NC}"
echo -e "${YELLOW}./deploy_kindle_dict.sh${NC}"

echo -e "${GREEN}Po zakończeniu wdrażania, aplikacja będzie dostępna pod adresem:${NC}"
echo -e "${GREEN}https://dict.c11.net.pl${NC}"
