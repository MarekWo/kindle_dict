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

# Tworzenie katalogów dla projektu
echo -e "${YELLOW}Tworzenie katalogów dla projektu...${NC}"
mkdir -p kindle_dict/{logs,nginx/ssl}

# Kopiowanie certyfikatów SSL
echo -e "${YELLOW}Kopiowanie certyfikatów SSL...${NC}"
cp /home/marek/ssl/config/live/dict.c11.net.pl/fullchain.pem kindle_dict/nginx/ssl/
cp /home/marek/ssl/config/live/dict.c11.net.pl/privkey.pem kindle_dict/nginx/ssl/
chmod 644 kindle_dict/nginx/ssl/*.pem

# Generowanie bezpiecznego klucza dla Django
echo -e "${YELLOW}Generowanie bezpiecznego klucza dla Django...${NC}"
DJANGO_SECRET_KEY=$(openssl rand -base64 50 | tr -dc 'a-zA-Z0-9!@#$%^&*(-_=+)' | head -c50)

# Aktualizacja pliku .env.prod
echo -e "${YELLOW}Aktualizacja pliku .env.prod...${NC}"
sed -i "s/SECRET_KEY=zmień_to_na_bezpieczny_klucz_produkcyjny/SECRET_KEY=$DJANGO_SECRET_KEY/" kindle_dict/.env.prod
echo -e "${GREEN}Plik .env.prod został zaktualizowany z bezpiecznym kluczem.${NC}"

echo -e "${YELLOW}Proszę zaktualizować hasło bazy danych w pliku .env.prod:${NC}"
echo -e "${YELLOW}nano kindle_dict/.env.prod${NC}"

echo -e "${GREEN}Konfiguracja środowiska produkcyjnego zakończona.${NC}"
echo -e "${GREEN}Aby uruchomić aplikację, wykonaj:${NC}"
echo -e "${YELLOW}cd kindle_dict${NC}"
echo -e "${YELLOW}docker-compose -f docker-compose.prod.yml up -d${NC}"

echo -e "${YELLOW}Aby wykonać migracje bazy danych, wykonaj:${NC}"
echo -e "${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py migrate${NC}"

echo -e "${YELLOW}Aby utworzyć superużytkownika, wykonaj:${NC}"
echo -e "${YELLOW}docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser${NC}"
