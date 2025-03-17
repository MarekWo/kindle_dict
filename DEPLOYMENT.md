# Wdrażanie aplikacji Kindle Dictionary Creator na serwer produkcyjny

Ten dokument zawiera instrukcje dotyczące wdrażania aplikacji Kindle Dictionary Creator na serwer produkcyjny.

## Wymagania

- Serwer z systemem Ubuntu
- Dostęp SSH do serwera
- Certyfikaty SSL dla domeny dict.c11.net.pl

## Przygotowane pliki

W repozytorium znajdują się następujące pliki konfiguracyjne do wdrożenia produkcyjnego:

- `docker/Dockerfile.prod` - Plik Dockerfile do budowy obrazu produkcyjnego
- `docker-compose.prod.yml` - Plik Docker Compose do uruchomienia kontenerów w środowisku produkcyjnym
- `nginx/nginx.conf` - Główny plik konfiguracyjny Nginx
- `nginx/conf.d/app.conf` - Konfiguracja wirtualnego hosta Nginx dla aplikacji
- `.env.prod` - Plik z zmiennymi środowiskowymi dla środowiska produkcyjnego (wymaga edycji)
- `setup_production.sh` - Skrypt do konfiguracji środowiska produkcyjnego na serwerze
- `deploy_to_production.sh` - Skrypt do wdrożenia aplikacji na serwer produkcyjny (kopiowanie plików lokalnych)
- `deploy_from_github.sh` - Skrypt do wdrożenia aplikacji na serwer produkcyjny (pobieranie z GitHub)

## Proces wdrażania

Istnieją dwie metody wdrażania aplikacji na serwer produkcyjny:

### Metoda 1: Wdrożenie z lokalnego repozytorium

Aby wdrożyć aplikację z lokalnego repozytorium na serwer produkcyjny, wykonaj następujące kroki:

1. Uruchom skrypt wdrożeniowy lokalnie:

```bash
./deploy_to_production.sh
```

Skrypt ten:
- Utworzy odpowiednie katalogi na serwerze
- Skopiuje pliki konfiguracyjne i kod źródłowy na serwer
- Nada uprawnienia do wykonania skryptu konfiguracyjnego

### Metoda 2: Wdrożenie z GitHub (zalecana)

Ponieważ projekt jest zsynchronizowany z GitHubem, możesz użyć tej metody, aby wdrożyć aplikację bezpośrednio z repozytorium GitHub:

1. Upewnij się, że wszystkie zmiany zostały wysłane do repozytorium GitHub:

```bash
git add .
git commit -m "Przygotowanie do wdrożenia produkcyjnego"
git push
```

2. Uruchom skrypt wdrożeniowy lokalnie:

```bash
./deploy_from_github.sh
```

Skrypt ten:
- Utworzy skrypt instalacyjny na serwerze
- Nada uprawnienia do wykonania skryptu instalacyjnego

3. Zaloguj się na serwer i uruchom skrypt instalacyjny:

```bash
ssh marek@dict.c11.net.pl
./deploy_kindle_dict.sh
```

Skrypt instalacyjny:
- Zainstaluje niezbędne zależności (Docker, Docker Compose, Git)
- Sklonuje repozytorium z GitHuba
- Skonfiguruje certyfikaty SSL
- Przygotuje plik .env.prod

### 2. Konfiguracja serwera

Po skopiowaniu plików na serwer, zaloguj się na serwer i dokończ konfigurację:

```bash
ssh marek@dict.c11.net.pl
cd kindle_dict
./setup_production.sh
```

Skrypt ten:
- Zaktualizuje system
- Zainstaluje Docker i Docker Compose (jeśli nie są zainstalowane)
- Skonfiguruje certyfikaty SSL
- Wygeneruje bezpieczny klucz dla Django
- Zaktualizuje plik .env.prod

### 3. Edycja pliku .env.prod (WAŻNE!)

Po uruchomieniu skryptu konfiguracyjnego, **koniecznie** należy edytować plik .env.prod, aby ustawić bezpieczne hasło dla bazy danych i skonfigurować inne zmienne środowiskowe:

```bash
nano kindle_dict/.env.prod
```

Zwróć szczególną uwagę na następujące zmienne:
- `SECRET_KEY` (powinna być już wygenerowana przez skrypt)
- `DB_PASSWORD` (ustaw bezpieczne hasło)
- Konfiguracja email (jeśli potrzebna)

**UWAGA**: Jeśli nie zaktualizujesz tych wartości przed uruchomieniem kontenerów, baza danych PostgreSQL nie uruchomi się poprawnie i pojawi się błąd:

```
Error: Database is uninitialized and superuser password is not specified.
       You must specify POSTGRES_PASSWORD to a non-empty value for the
       superuser.
```

Ponadto, podczas wykonywania poleceń Docker Compose, mogą pojawić się ostrzeżenia o brakujących zmiennych środowiskowych:

```
WARN[0000] The "DB_USER" variable is not set. Defaulting to a blank string. 
WARN[0000] The "DB_PASSWORD" variable is not set. Defaulting to a blank string. 
WARN[0000] The "DB_NAME" variable is not set. Defaulting to a blank string. 
```

### 4. Uruchomienie aplikacji

Po zakończeniu konfiguracji i **po edycji pliku .env.prod**, uruchom aplikację:

```bash
cd kindle_dict
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Wykonanie migracji bazy danych

Po uruchomieniu kontenerów, wykonaj migracje bazy danych:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 6. Utworzenie superużytkownika

Utwórz superużytkownika, aby mieć dostęp do panelu administracyjnego:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## Dostęp do aplikacji

Po zakończeniu wdrażania, aplikacja będzie dostępna pod adresem:

```
https://dict.c11.net.pl
```

Panel administracyjny będzie dostępny pod adresem:

```
https://dict.c11.net.pl/admin/
```

## Zarządzanie aplikacją

### Zatrzymanie aplikacji

```bash
cd kindle_dict
docker-compose -f docker-compose.prod.yml down
```

### Ponowne uruchomienie aplikacji

```bash
cd kindle_dict
docker-compose -f docker-compose.prod.yml up -d
```

### Przeglądanie logów

```bash
cd kindle_dict
docker-compose -f docker-compose.prod.yml logs -f
```

### Aktualizacja aplikacji

Istnieją dwie metody aktualizacji aplikacji:

#### Metoda 1: Aktualizacja z lokalnego repozytorium

```bash
# Lokalnie
./deploy_to_production.sh

# Na serwerze
cd kindle_dict
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

#### Metoda 2: Aktualizacja z GitHub (zalecana)

```bash
# Lokalnie - wypchnij zmiany do GitHuba
git add .
git commit -m "Aktualizacja aplikacji"
git push

# Lokalnie - uruchom skrypt wdrożeniowy
./deploy_from_github.sh

# Na serwerze
ssh marek@dict.c11.net.pl
cd kindle_dict
git pull  # Pobierz najnowsze zmiany z GitHuba
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

Możesz również użyć przygotowanego skryptu do utworzenia skryptu aktualizacyjnego na serwerze:

```bash
# Lokalnie
./create_update_script.sh
```

Skrypt ten utworzy na serwerze plik `update_kindle_dict.sh`, który:
- Pobierze najnowsze zmiany z GitHuba
- Zatrzyma kontenery
- Uruchomi kontenery z przebudową obrazów
- Wykona migracje bazy danych
- Zbierze pliki statyczne

Następnie, aby zaktualizować aplikację, wystarczy uruchomić:

```bash
ssh marek@dict.c11.net.pl "./update_kindle_dict.sh"
```

Ten sposób aktualizacji jest najbardziej zalecany, ponieważ automatyzuje wszystkie niezbędne kroki.

## Rozwiązywanie problemów

### Problem z synchronizacją czasu podczas budowania obrazu Docker

Jeśli podczas budowania obrazu Docker pojawi się błąd związany z repozytorium Debian Security, taki jak:

```
E: Release file for http://deb.debian.org/debian-security/dists/bookworm-security/InRelease is not valid yet (invalid for another X min X sec). Updates for this repository will not be applied.
```

Jest to spowodowane problemem z synchronizacją czasu na serwerze. W pliku `Dockerfile.prod` dodaliśmy opcję `--allow-releaseinfo-change` do poleceń `apt-get update` oraz dodaliśmy `|| true`, aby ignorować błędy związane z repozytorium debian-security.

Jeśli problem nadal występuje, możesz spróbować zsynchronizować czas na serwerze:

```bash
sudo apt-get install -y ntpdate
sudo ntpdate pool.ntp.org
```

### Problem z zależnościami pośrednimi podczas budowania obrazu Docker

Jeśli podczas budowania obrazu Docker pojawi się błąd związany z brakującymi zależnościami pośrednimi, taki jak:

```
ERROR: Could not find a version that satisfies the requirement asgiref<4,>=3.6.0 (from django)
ERROR: No matching distribution found for asgiref<4,>=3.6.0
```

Jest to spowodowane tym, że w wieloetapowym procesie budowania obrazu Docker, używamy `pip wheel` do tworzenia kół (wheels) dla zależności. W pliku `Dockerfile.prod` usunęliśmy opcję `--no-deps` z polecenia `pip wheel`, aby uwzględnić zależności pośrednie.

Jeśli problem nadal występuje, możesz dodać brakujące zależności bezpośrednio do pliku `requirements.txt`.

### Problem z SECRET_KEY podczas budowania obrazu Docker

Jeśli podczas budowania obrazu Docker pojawi się błąd związany z brakującym kluczem SECRET_KEY, taki jak:

```
django.core.exceptions.ImproperlyConfigured: Set the SECRET_KEY environment variable
```

Jest to spowodowane tym, że podczas budowania obrazu Docker, próbujemy uruchomić polecenie `collectstatic`, które wymaga zmiennej środowiskowej SECRET_KEY. W pliku `Dockerfile.prod` usunęliśmy polecenie `collectstatic` z etapu budowania obrazu i przenieśliśmy je do etapu uruchamiania kontenera.

Po uruchomieniu kontenera, należy ręcznie uruchomić polecenie `collectstatic`:

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput --settings=kindle_dict.settings.prod
```

### Sprawdzanie statusu kontenerów

```bash
docker-compose -f docker-compose.prod.yml ps
```

### Sprawdzanie logów konkretnego kontenera

```bash
docker-compose -f docker-compose.prod.yml logs -f [nazwa_kontenera]
```

Dostępne kontenery:
- `web` - Aplikacja Django
- `db` - Baza danych PostgreSQL
- `redis` - Redis
- `celery` - Celery worker
- `celery_beat` - Celery beat
- `nginx` - Serwer Nginx

### Restart konkretnego kontenera

```bash
docker-compose -f docker-compose.prod.yml restart [nazwa_kontenera]
```

## Automatyczne odnawianie certyfikatów SSL

Certyfikaty SSL są już skonfigurowane do automatycznego odnawiania na serwerze. Jeśli jednak wystąpią problemy, można ręcznie skopiować odnowione certyfikaty do katalogu nginx/ssl:

```bash
cp /home/marek/ssl/config/live/dict.c11.net.pl/fullchain.pem kindle_dict/nginx/ssl/
cp /home/marek/ssl/config/live/dict.c11.net.pl/privkey.pem kindle_dict/nginx/ssl/
chmod 644 kindle_dict/nginx/ssl/*.pem
docker-compose -f docker-compose.prod.yml restart nginx
```
