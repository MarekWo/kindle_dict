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
- `.env.example` - Przykładowy plik z zmiennymi środowiskowymi (kopiowany do `.env` podczas wdrażania)
- `setup_production.sh` - Skrypt do konfiguracji środowiska produkcyjnego na serwerze
- `deploy_to_production.sh` - Skrypt do wdrożenia aplikacji na serwer produkcyjny (kopiowanie plików lokalnych)
- `deploy_from_github.sh` - Skrypt do wdrożenia aplikacji na serwer produkcyjny (pobieranie z GitHub)

## Proces wdrażania

### Ważna uwaga: Uruchomienie skryptu process_kindlegen_jobs.py

Aby aplikacja mogła generować pliki .mobi, konieczne jest uruchomienie skryptu `process_kindlegen_jobs.py` na serwerze produkcyjnym. Skrypt ten musi działać poza kontenerem Docker, bezpośrednio na hoście.

1. Zainstaluj wymagane zależności na serwerze:
   ```bash
   # Instalacja Wine (wymagane dla kindlegen.exe)
   sudo apt install wine
   
   # Włączenie obsługi architektury 32-bitowej (kindlegen.exe jest 32-bitowy)
   sudo dpkg --add-architecture i386
   
   # Aktualizacja repozytoriów
   sudo apt update
   
   # Instalacja wine32
   sudo apt install wine32
   ```

2. Uruchom skrypt w trybie ciągłym (zalecane jako usługa systemowa):

   **UWAGA**: Standardowy użytkownik może nie mieć dostępu do katalogu `/var/lib/docker/volumes`. W takim przypadku należy utworzyć alternatywny katalog i skonfigurować aplikację, aby korzystała z niego.

   ```bash
   # Utwórz alternatywny katalog dla plików kindlegen
   sudo mkdir -p /opt/kindle_dict/media/kindlegen_jobs

   # Ustaw odpowiednie uprawnienia
   sudo chown -R marek:marek /opt/kindle_dict

   # Utwórz plik usługi systemowej
   sudo nano /etc/systemd/system/kindlegen-processor.service
   ```

   Zawartość pliku:
   ```
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
   ```

   **UWAGA**: Zastąp `$USER` i `$PWD` rzeczywistymi wartościami dla Twojego środowiska.

   Następnie:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable kindlegen-processor
   sudo systemctl start kindlegen-processor
   ```

   **WAŻNE**: Jeśli używasz alternatywnego katalogu `/opt/kindle_dict/media`, musisz również skonfigurować kontenery Docker, aby korzystały z tego samego katalogu. W pliku `docker-compose.prod.yml` zmień:

   ```yaml
   volumes:
     - media_volume:/app/media
   ```

   na:

   ```yaml
   volumes:
     - /opt/kindle_dict/media:/app/media
   ```

   Alternatywnie, możesz utworzyć dowiązanie symboliczne:

   ```bash
   sudo ln -s /opt/kindle_dict/media /var/lib/docker/volumes/kindle_dict_media_volume/_data
   ```

3. Alternatywnie, możesz uruchomić skrypt w tle za pomocą nohup:
   ```bash
   nohup python scripts/process_kindlegen_jobs.py --media-root=/var/lib/docker/volumes/kindle_dict_media_volume/_data --kindlegen-path=./src/tools/kindlegen.exe > kindlegen_processor.log 2>&1 &
   ```

4. Sprawdź, czy skrypt działa poprawnie:
   ```bash
   # Dla usługi systemowej
   sudo systemctl status kindlegen-processor
   
   # Dla nohup
   tail -f kindlegen_processor.log
   ```

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
- Przygotuje plik .env

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
- Zaktualizuje plik .env

### 3. Edycja pliku .env (WAŻNE!)

Po uruchomieniu skryptu konfiguracyjnego, **koniecznie** należy edytować plik .env, aby ustawić bezpieczne hasło dla bazy danych i skonfigurować inne zmienne środowiskowe:

```bash
nano kindle_dict/.env
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


### 4. Uruchomienie aplikacji

Po zakończeniu konfiguracji i **po edycji pliku .env**, uruchom aplikację:

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

### Problem z CSRF za proxy

Jeśli po wdrożeniu aplikacji pojawia się błąd "Dostęp zabroniony (403) - Weryfikacja CSRF nie powiodła się. Żądanie zostało przerwane" podczas próby logowania lub wysyłania formularzy, może to być spowodowane niepoprawną konfiguracją nagłówków proxy.

Aby rozwiązać ten problem:

1. Upewnij się, że w pliku `nginx/conf.d/app.conf` są ustawione odpowiednie nagłówki proxy:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Server $host;
```

2. Upewnij się, że w pliku `src/kindle_dict/settings/prod.py` jest ustawiona lista zaufanych źródeł dla CSRF:

```python
CSRF_TRUSTED_ORIGINS = ["https://dict.c11.net.pl"]
```

### Problem z podwójnymi przekierowaniami SSL

Jeśli po wdrożeniu aplikacji pojawia się błąd "Pętla przekierowań - Firefox has detected that the server is redirecting the request for this address in a way that will never complete", może to być spowodowane podwójnymi przekierowaniami SSL.

Aby rozwiązać ten problem:

1. Upewnij się, że w pliku `src/kindle_dict/settings/prod.py` jest ustawione:

```python
SECURE_SSL_REDIRECT = False  # Nginx już obsługuje przekierowania
```

2. Upewnij się, że w pliku `nginx/conf.d/app.conf` jest poprawnie skonfigurowane przekierowanie HTTP na HTTPS:

```nginx
server {
    listen 80;
    server_name dict.c11.net.pl;
    
    # Przekierowanie HTTP na HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
```

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

### Problem z interpolacją zmiennych środowiskowych w Docker Compose

Docker Compose w pierwszej kolejności "wstrzykuje" zmienne "z zewnątrz" (czyli z pliku `.env` lub zmiennych systemowych powłoki) do samego pliku docker-compose – dopiero potem uruchamia kontenery i czyta sekcję `env_file`. 

W pliku `docker-compose.prod.yml` używamy składni `${DB_USER}`, `${DB_PASSWORD}` i `${DB_NAME}`, które są zastępowane wartościami z pliku `.env`. Dlatego ważne jest, aby plik `.env` zawierał poprawne wartości tych zmiennych.

```yaml
environment:
  - POSTGRES_USER=${DB_USER}
  - POSTGRES_PASSWORD=${DB_PASSWORD}
  - POSTGRES_DB=${DB_NAME}
```

Jeśli chcesz zmienić te wartości, musisz edytować plik `.env`.

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

Certyfikaty SSL są skonfigurowane do automatycznego odnawiania na serwerze przez Let's Encrypt. Aby odnowione certyfikaty były automatycznie dostępne dla aplikacji, zalecamy użycie skryptu hook, który będzie automatycznie kopiował odnowione certyfikaty do katalogu nginx/ssl i restartował kontener nginx.

### Skrypt hook po odnowieniu certyfikatu (ZALECANE)

To rozwiązanie wykorzystuje mechanizm hooków Certbota, który pozwala na wykonanie skryptu po pomyślnym odnowieniu certyfikatu.

1. Skopiuj skrypt `certbot-renewal-hook.sh` do katalogu `~/ssl/config/renewal-hooks/post/` na serwerze:

```bash
mkdir -p ~/ssl/config/renewal-hooks/post/
cp certbot-renewal-hook.sh ~/ssl/config/renewal-hooks/post/
chmod +x ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh
```

2. Dostosuj zmienne w skrypcie do swojego środowiska (jeśli to konieczne).

3. Przetestuj skrypt, uruchamiając go ręcznie:

```bash
~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh
```

4. Upewnij się, że skrypt jest wywoływany po odnowieniu certyfikatu:

```bash
# Dodaj ścieżkę do skryptu w konfiguracji certbota
echo "renew_hook = ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh" >> ~/ssl/config/renewal/dict.c11.net.pl.conf
```

Szczegółowe instrukcje dotyczące wdrożenia tego rozwiązania znajdują się w pliku `SSL_RENEWAL_README.md`.

### Ręczne kopiowanie certyfikatów (niezalecane)

Jeśli z jakiegoś powodu powyższe rozwiązanie nie działa, można ręcznie skopiować odnowione certyfikaty do katalogu nginx/ssl:

```bash
# Ustaw ścieżkę do certyfikatów Let's Encrypt
SSL_CERT_PATH="$HOME/ssl/config/live/dict.c11.net.pl"

# Kopiuj certyfikaty
cp "${SSL_CERT_PATH}/fullchain.pem" kindle_dict/nginx/ssl/
cp "${SSL_CERT_PATH}/privkey.pem" kindle_dict/nginx/ssl/
chmod 644 kindle_dict/nginx/ssl/*.pem

# Restart kontenera nginx
docker-compose -f docker-compose.prod.yml restart nginx
```
