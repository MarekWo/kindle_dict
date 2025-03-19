#!/bin/bash

# Skrypt do konfiguracji środowiska produkcyjnego na serwerze dict.c11.net.pl
# Uruchom ten skrypt na serwerze produkcyjnym

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Rozpoczynam konfigurację środowiska produkcyjnego...${NC}"

# Aktualizacja systemu
echo -e "${YELLOW}Aktualizacja systemu...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Instalacja Dockera
echo -e "${YELLOW}Instalacja Dockera...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker nie jest zainstalowany. Instaluję...${NC}"
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker $USER
    echo -e "${GREEN}Docker został zainstalowany.${NC}"
else
    echo -e "${GREEN}Docker jest już zainstalowany.${NC}"
fi

# Instalacja Docker Compose
echo -e "${YELLOW}Instalacja Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose nie jest zainstalowany. Instaluję...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose został zainstalowany.${NC}"
else
    echo -e "${GREEN}Docker Compose jest już zainstalowany.${NC}"
fi

# Instalacja Wine i Wine32 (potrzebne dla kindlegen.exe)
echo -e "${YELLOW}Instalacja Wine i Wine32...${NC}"
if ! command -v wine &> /dev/null; then
    echo -e "${YELLOW}Wine nie jest zainstalowany. Instaluję...${NC}"
    sudo apt-get install -y wine
    
    # Włączenie obsługi architektury 32-bitowej
    echo -e "${YELLOW}Włączanie obsługi architektury 32-bitowej...${NC}"
    sudo dpkg --add-architecture i386
    sudo apt-get update
    
    # Instalacja wine32
    echo -e "${YELLOW}Instalacja wine32...${NC}"
    sudo apt-get install -y wine32
    
    echo -e "${GREEN}Wine i Wine32 zostały zainstalowane.${NC}"
else
    echo -e "${GREEN}Wine jest już zainstalowany. Sprawdzam wine32...${NC}"
    if dpkg -l | grep -q wine32; then
        echo -e "${GREEN}Wine32 jest już zainstalowany.${NC}"
    else
        echo -e "${YELLOW}Wine32 nie jest zainstalowany. Instaluję...${NC}"
        # Włączenie obsługi architektury 32-bitowej
        sudo dpkg --add-architecture i386
        sudo apt-get update
        
        # Instalacja wine32
        sudo apt-get install -y wine32
        echo -e "${GREEN}Wine32 został zainstalowany.${NC}"
    fi
fi

# Tworzenie katalogów dla projektu
echo -e "${YELLOW}Tworzenie katalogów dla projektu...${NC}"
mkdir -p kindle_dict/{logs,nginx/ssl}

# Tworzenie katalogu dla plików kindlegen
echo -e "${YELLOW}Tworzenie katalogu dla plików kindlegen...${NC}"
sudo mkdir -p /opt/kindle_dict/media/kindlegen_jobs
sudo chown -R $USER:$USER /opt/kindle_dict
echo -e "${GREEN}Katalog /opt/kindle_dict/media został utworzony.${NC}"

# Kopiowanie certyfikatów SSL
echo -e "${YELLOW}Kopiowanie certyfikatów SSL...${NC}"
cp /home/marek/ssl/config/live/dict.c11.net.pl/fullchain.pem kindle_dict/nginx/ssl/
cp /home/marek/ssl/config/live/dict.c11.net.pl/privkey.pem kindle_dict/nginx/ssl/
chmod 644 kindle_dict/nginx/ssl/*.pem

# Generowanie bezpiecznego klucza dla Django
echo -e "${YELLOW}Generowanie bezpiecznego klucza dla Django...${NC}"
DJANGO_SECRET_KEY=$(openssl rand -base64 50 | tr -dc 'a-zA-Z0-9!@#$%^&*(-_=+)' | head -c50)

# Aktualizacja pliku .env
echo -e "${YELLOW}Aktualizacja pliku .env...${NC}"
if [ -f "kindle_dict/.env" ]; then
    sed -i "s/SECRET_KEY=your_secret_key_here/SECRET_KEY=$DJANGO_SECRET_KEY/" kindle_dict/.env
    echo -e "${GREEN}Plik .env został zaktualizowany z bezpiecznym kluczem.${NC}"
else
    echo -e "${YELLOW}Tworzenie pliku .env...${NC}"
    cp kindle_dict/.env.example kindle_dict/.env
    sed -i "s/DEBUG=True/DEBUG=False/" kindle_dict/.env
    sed -i "s/SECRET_KEY=your_secret_key_here/SECRET_KEY=$DJANGO_SECRET_KEY/" kindle_dict/.env
    sed -i "s/ALLOWED_HOSTS=localhost,127.0.0.1/ALLOWED_HOSTS=dict.c11.net.pl,localhost,127.0.0.1/" kindle_dict/.env
    echo -e "${GREEN}Plik .env został utworzony.${NC}"
fi

echo -e "${RED}WAŻNE: Musisz zaktualizować hasło bazy danych w pliku .env przed uruchomieniem kontenerów!${NC}"
echo -e "${RED}Jeśli tego nie zrobisz, baza danych nie uruchomi się poprawnie.${NC}"
echo -e "${YELLOW}nano kindle_dict/.env${NC}"

echo -e "${GREEN}Konfiguracja środowiska produkcyjnego zakończona.${NC}"
echo -e "${RED}WAŻNE: Przed uruchomieniem aplikacji, upewnij się, że zaktualizowałeś plik .env!${NC}"
echo -e "${GREEN}Aby uruchomić aplikację, wykonaj:${NC}"
echo -e "${YELLOW}cd kindle_dict${NC}"
echo -e "${YELLOW}docker-compose -f docker-compose.prod.yml up -d${NC}"

echo -e "${YELLOW}Aby wykonać migracje bazy danych, wykonaj:${NC}"
echo -e "${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py migrate${NC}"

echo -e "${YELLOW}Aby utworzyć superużytkownika, wykonaj:${NC}"
echo -e "${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser${NC}"

# Konfiguracja usługi systemowej kindlegen-processor
echo -e "${YELLOW}Konfiguracja usługi systemowej kindlegen-processor...${NC}"
KINDLEGEN_SERVICE_FILE="/etc/systemd/system/kindlegen-processor.service"

# Tworzenie pliku usługi systemowej
echo -e "${YELLOW}Tworzenie pliku usługi systemowej...${NC}"
sudo tee $KINDLEGEN_SERVICE_FILE > /dev/null << EOL
[Unit]
Description=Kindle Dictionary Kindlegen Processor
After=network.target

[Service]
User=$USER
WorkingDirectory=$PWD/kindle_dict
ExecStart=/usr/bin/python3 $PWD/kindle_dict/scripts/process_kindlegen_jobs.py --media-root=/opt/kindle_dict/media --kindlegen-path=$PWD/kindle_dict/src/tools/kindlegen.exe
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# Przeładowanie konfiguracji systemd
echo -e "${YELLOW}Przeładowanie konfiguracji systemd...${NC}"
sudo systemctl daemon-reload

# Włączenie usługi
echo -e "${YELLOW}Włączenie usługi kindlegen-processor...${NC}"
sudo systemctl enable kindlegen-processor

echo -e "${GREEN}Usługa kindlegen-processor została skonfigurowana.${NC}"
echo -e "${YELLOW}Aby uruchomić usługę, wykonaj:${NC}"
echo -e "${YELLOW}sudo systemctl start kindlegen-processor${NC}"
echo -e "${YELLOW}Aby sprawdzić status usługi, wykonaj:${NC}"
echo -e "${YELLOW}sudo systemctl status kindlegen-processor${NC}"
