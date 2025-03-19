# Automatyczne odnawianie certyfikatów SSL

W tym dokumencie przedstawiono dwa rozwiązania problemu automatycznego odnawiania certyfikatów SSL dla aplikacji Kindle Dictionary.

## Problem

Certyfikaty Let's Encrypt są automatycznie odnawiane co 3 miesiące, ale odnowione certyfikaty nie są automatycznie widoczne w kontenerze nginx, co wymaga ręcznego kopiowania plików i restartowania kontenera.

## Rozwiązanie 1: Bezpośrednie montowanie katalogu z certyfikatami (ZALECANE)

To rozwiązanie eliminuje potrzebę kopiowania certyfikatów, montując katalog z certyfikatami Let's Encrypt bezpośrednio do kontenera nginx.

### Kroki wdrożenia:

1. Zatrzymaj bieżące kontenery:

```bash
cd ~/kindle_dict
docker-compose -f docker-compose.prod.yml down
```

2. Zastąp plik `docker-compose.prod.yml` nowym plikiem `docker-compose.prod.direct-ssl.yml`:

```bash
cp docker-compose.prod.direct-ssl.yml docker-compose.prod.yml
```

3. **WAŻNE**: Dostosuj ścieżkę do certyfikatów SSL w pliku `.env`:

```bash
# Dodaj tę linię do pliku .env
SSL_CERT_PATH=$HOME/ssl/config/live/twoja-domena.pl
```

Zastąp `$HOME/ssl/config/live/twoja-domena.pl` rzeczywistą ścieżką do katalogu z certyfikatami Let's Encrypt na Twoim serwerze. Domyślnie skrypt używa ścieżki `$HOME/ssl/config/live/dict.c11.net.pl`.

4. Uruchom ponownie kontenery:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Po wdrożeniu tego rozwiązania, kontener nginx będzie miał bezpośredni dostęp do katalogu z certyfikatami Let's Encrypt, więc odnowione certyfikaty będą automatycznie widoczne bez potrzeby kopiowania.

## Rozwiązanie 2: Skrypt hook po odnowieniu certyfikatu

To rozwiązanie wykorzystuje mechanizm hooków Certbota, który pozwala na wykonanie skryptu po pomyślnym odnowieniu certyfikatu.

### Kroki wdrożenia:

1. Skopiuj skrypt `certbot-renewal-hook.sh` do katalogu `/etc/letsencrypt/renewal-hooks/post/` na serwerze:

```bash
sudo cp certbot-renewal-hook.sh /etc/letsencrypt/renewal-hooks/post/
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/certbot-renewal-hook.sh
```

2. **WAŻNE**: Dostosuj zmienne w skrypcie do swojego środowiska. Otwórz skrypt w edytorze:

```bash
sudo nano /etc/letsencrypt/renewal-hooks/post/certbot-renewal-hook.sh
```

I dostosuj następujące zmienne:
- `DOMAIN` - nazwa Twojej domeny (np. "twoja-domena.pl")
- `CERT_SOURCE` - ścieżka do katalogu z certyfikatami Let's Encrypt
- `CERT_DEST` - ścieżka do katalogu nginx/ssl w aplikacji
- `CONTAINER_NAME` - nazwa kontenera nginx

Możesz również ustawić te zmienne jako zmienne środowiskowe w systemie.

3. Przetestuj skrypt, uruchamiając go ręcznie:

```bash
sudo /etc/letsencrypt/renewal-hooks/post/certbot-renewal-hook.sh
```

Po wdrożeniu tego rozwiązania, za każdym razem, gdy certyfikat zostanie odnowiony przez Certbot, skrypt automatycznie skopiuje nowe certyfikaty do katalogu nginx i zrestartuje kontener.

## Zalecane rozwiązanie

Zdecydowanie zalecamy wdrożenie **Rozwiązania 1** (bezpośrednie montowanie), ponieważ:
- Eliminuje potrzebę kopiowania plików
- Jest bardziej niezawodne (nie ma ryzyka, że skrypt nie zadziała)
- Jest prostsze w utrzymaniu
- Nie wymaga restartowania kontenera nginx po odnowieniu certyfikatu

## Uwagi

- Oba rozwiązania wymagają, aby certyfikaty Let's Encrypt były już poprawnie skonfigurowane i automatycznie odnawiane.
- W przypadku Rozwiązania 1, upewnij się, że kontener nginx ma odpowiednie uprawnienia do odczytu plików certyfikatów.
- **WAŻNE**: Wszystkie ścieżki w plikach konfiguracyjnych zostały zmodyfikowane, aby używać zmiennych środowiskowych zamiast sztywno zakodowanych ścieżek. Upewnij się, że dostosowałeś te zmienne do swojego środowiska.
