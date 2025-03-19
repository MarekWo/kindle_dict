#!/bin/bash

# Skrypt do automatycznego kopiowania odnowionych certyfikatów Let's Encrypt
# i restartowania kontenera nginx
# Ten skrypt powinien być umieszczony w katalogu /etc/letsencrypt/renewal-hooks/post/

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Konfiguracja
DOMAIN="${DOMAIN:-dict.c11.net.pl}"
# Domyślna ścieżka dla certyfikatów Let's Encrypt, można dostosować
CERT_SOURCE="${SSL_CERT_PATH:-$HOME/ssl/config/live/$DOMAIN}"
# Ścieżka do katalogu nginx/ssl w aplikacji
CERT_DEST="${APP_DIR:-$HOME/kindle_dict}/nginx/ssl"
CONTAINER_NAME="kindle_dict_nginx"

echo -e "${YELLOW}Certyfikat dla $DOMAIN został odnowiony. Kopiowanie do katalogu nginx...${NC}"

# Kopiowanie certyfikatów
cp $CERT_SOURCE/fullchain.pem $CERT_DEST/
cp $CERT_SOURCE/privkey.pem $CERT_DEST/
chmod 644 $CERT_DEST/*.pem

echo -e "${GREEN}Certyfikaty zostały skopiowane.${NC}"

# Restart kontenera nginx
echo -e "${YELLOW}Restartowanie kontenera nginx...${NC}"
docker restart $CONTAINER_NAME

echo -e "${GREEN}Kontener nginx został zrestartowany.${NC}"
echo -e "${GREEN}Odnowione certyfikaty są teraz używane przez serwer.${NC}"
