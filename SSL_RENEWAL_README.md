# Automatyczne odnawianie certyfikatów SSL

W tym dokumencie przedstawiono rozwiązanie problemu automatycznego odnawiania certyfikatów SSL dla aplikacji Kindle Dictionary.

## Problem

Certyfikaty Let's Encrypt są automatycznie odnawiane co 3 miesiące, ale odnowione certyfikaty nie są automatycznie widoczne w kontenerze nginx, co wymaga ręcznego kopiowania plików i restartowania kontenera.

## Rozwiązanie: Skrypt hook po odnowieniu certyfikatu (ZALECANE)

To rozwiązanie wykorzystuje mechanizm hooków Certbota, który pozwala na wykonanie skryptu po pomyślnym odnowieniu certyfikatu. Skrypt automatycznie kopiuje odnowione certyfikaty do katalogu nginx/ssl i restartuje kontener nginx.

### Kroki wdrożenia:

1. Skopiuj skrypt `certbot-renewal-hook.sh` do katalogu `~/ssl/config/renewal-hooks/post/` na serwerze:

```bash
mkdir -p ~/ssl/config/renewal-hooks/post/
cp certbot-renewal-hook.sh ~/ssl/config/renewal-hooks/post/
chmod +x ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh
```

2. **WAŻNE**: Dostosuj zmienne w skrypcie do swojego środowiska. Otwórz skrypt w edytorze:

```bash
nano ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh
```

I dostosuj następujące zmienne:
- `DOMAIN` - nazwa Twojej domeny (np. "twoja-domena.pl")
- `CERT_SOURCE` - ścieżka do katalogu z certyfikatami Let's Encrypt
- `CERT_DEST` - ścieżka do katalogu nginx/ssl w aplikacji
- `CONTAINER_NAME` - nazwa kontenera nginx

Domyślne wartości są już ustawione dla typowej instalacji:
```bash
DOMAIN="${DOMAIN:-dict.c11.net.pl}"
CERT_SOURCE="${SSL_CERT_PATH:-$HOME/ssl/config/live/$DOMAIN}"
CERT_DEST="${APP_DIR:-$HOME/kindle_dict}/nginx/ssl"
CONTAINER_NAME="kindle_dict_nginx"
```

3. Przetestuj skrypt, uruchamiając go ręcznie:

```bash
~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh
```

4. Upewnij się, że skrypt jest wywoływany po odnowieniu certyfikatu. Możesz to zrobić, dodając ścieżkę do skryptu w konfiguracji certbota lub tworząc dowiązanie symboliczne:

```bash
# Opcja 1: Dodaj ścieżkę do skryptu w konfiguracji certbota
echo "renew_hook = ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh" >> ~/ssl/config/renewal/dict.c11.net.pl.conf

# Opcja 2: Utwórz dowiązanie symboliczne w katalogu renewal-hooks/post
ln -s ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh ~/ssl/config/renewal-hooks/post/certbot-renewal-hook.sh
```

Po wdrożeniu tego rozwiązania, za każdym razem, gdy certyfikat zostanie odnowiony przez Certbot, skrypt automatycznie skopiuje nowe certyfikaty do katalogu nginx i zrestartuje kontener.

## Uwagi

- To rozwiązanie wymaga, aby certyfikaty Let's Encrypt były już poprawnie skonfigurowane i automatycznie odnawiane.
- Skrypt kopiuje certyfikaty do dedykowanego katalogu nginx/ssl, do którego kontener nginx ma dostęp, co eliminuje problemy z uprawnieniami.
- Skrypt restartuje kontener nginx, aby załadował nowe certyfikaty.
- **WAŻNE**: Wszystkie ścieżki w plikach konfiguracyjnych zostały zmodyfikowane, aby używać zmiennych środowiskowych zamiast sztywno zakodowanych ścieżek. Upewnij się, że dostosowałeś te zmienne do swojego środowiska.
