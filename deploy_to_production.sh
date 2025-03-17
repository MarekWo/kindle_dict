#!/bin/bash

# Skrypt do wdrożenia aplikacji na serwer produkcyjny dict.c11.net.pl
# Uruchom ten skrypt lokalnie

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Konfiguracja
SERVER="marek@dict.c11.net.pl"
REMOTE_DIR="kindle_dict"

echo -e "${GREEN}Rozpoczynam wdrażanie aplikacji na serwer produkcyjny...${NC}"

# Tworzenie katalogu na serwerze
echo -e "${YELLOW}Tworzenie katalogów na serwerze...${NC}"
ssh $SERVER "mkdir -p $REMOTE_DIR/docker $REMOTE_DIR/src $REMOTE_DIR/nginx/conf.d $REMOTE_DIR/nginx/ssl"

# Kopiowanie plików konfiguracyjnych
echo -e "${YELLOW}Kopiowanie plików konfiguracyjnych...${NC}"
scp docker/Dockerfile.prod $SERVER:$REMOTE_DIR/docker/
scp docker-compose.prod.yml $SERVER:$REMOTE_DIR/
scp nginx/nginx.conf $SERVER:$REMOTE_DIR/nginx/
scp nginx/conf.d/app.conf $SERVER:$REMOTE_DIR/nginx/conf.d/
scp .env.prod $SERVER:$REMOTE_DIR/
scp requirements.txt $SERVER:$REMOTE_DIR/
scp setup_production.sh $SERVER:$REMOTE_DIR/

# Kopiowanie kodu źródłowego
echo -e "${YELLOW}Kopiowanie kodu źródłowego...${NC}"
scp -r src/* $SERVER:$REMOTE_DIR/src/

# Nadanie uprawnień do wykonania skryptu
echo -e "${YELLOW}Nadanie uprawnień do wykonania skryptu...${NC}"
ssh $SERVER "chmod +x $REMOTE_DIR/setup_production.sh"

echo -e "${GREEN}Pliki zostały skopiowane na serwer.${NC}"
echo -e "${YELLOW}Aby dokończyć konfigurację, zaloguj się na serwer i uruchom:${NC}"
echo -e "${YELLOW}ssh $SERVER${NC}"
echo -e "${YELLOW}cd $REMOTE_DIR${NC}"
echo -e "${YELLOW}./setup_production.sh${NC}"

echo -e "${GREEN}Po zakończeniu konfiguracji, aplikacja będzie dostępna pod adresem:${NC}"
echo -e "${GREEN}https://dict.c11.net.pl${NC}"
