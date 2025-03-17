#!/bin/bash

# Skrypt do utworzenia skryptu aktualizacyjnego na serwerze
# Uruchom ten skrypt lokalnie

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Konfiguracja
SERVER="marek@dict.c11.net.pl"

echo -e "${GREEN}Tworzenie skryptu aktualizacyjnego na serwerze...${NC}"

ssh $SERVER "cat > ~/update_kindle_dict.sh << 'EOL'
#!/bin/bash

# Kolory do wyróżnienia komunikatów
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e \"\${GREEN}Rozpoczynam aktualizację aplikacji Kindle Dictionary Creator...\${NC}\"

# Przejście do katalogu projektu
cd kindle_dict

# Pobranie najnowszych zmian z GitHuba
echo -e \"\${YELLOW}Pobieranie najnowszych zmian z GitHuba...\${NC}\"
git pull

# Zatrzymanie kontenerów
echo -e \"\${YELLOW}Zatrzymywanie kontenerów...\${NC}\"
docker-compose -f docker-compose.prod.yml down

# Uruchomienie kontenerów z przebudową obrazów
echo -e \"\${YELLOW}Uruchamianie kontenerów z przebudową obrazów...\${NC}\"
docker-compose -f docker-compose.prod.yml up -d --build

# Wykonanie migracji bazy danych
echo -e \"\${YELLOW}Wykonywanie migracji bazy danych...\${NC}\"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate

# Zbieranie plików statycznych
echo -e \"\${YELLOW}Zbieranie plików statycznych...\${NC}\"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

echo -e \"\${GREEN}Aktualizacja aplikacji zakończona pomyślnie.\${NC}\"
echo -e \"\${GREEN}Aplikacja jest dostępna pod adresem: https://dict.c11.net.pl\${NC}\"
EOL"

# Nadanie uprawnień do wykonania skryptu
ssh $SERVER "chmod +x ~/update_kindle_dict.sh"

echo -e "${GREEN}Skrypt aktualizacyjny został utworzony na serwerze.${NC}"
echo -e "${YELLOW}Aby zaktualizować aplikację, wykonaj:${NC}"
echo -e "${YELLOW}ssh $SERVER \"./update_kindle_dict.sh\"${NC}"
