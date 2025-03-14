# Kreator Słownika Kindle

Aplikacja webowa do tworzenia słowników dla urządzeń Kindle, zbudowana na Django z interfejsem webowym.

## Funkcjonalności

- Tworzenie słowników Kindle z plików tekstowych
- Generowanie wszystkich potrzebnych plików: HTML, OPF, JPG, MOBI, JSON
- Asynchroniczne przetwarzanie zadań z użyciem Celery i Redis
- Repozytorium publicznych słowników

## Wymagania

- Docker i Docker Compose
- Wine (do obsługi kindlegen.exe na Linuxie)
- kindlegen.exe (narzędzie Amazon do tworzenia plików MOBI)

## Pierwsze uruchomienie

1. Sklonuj repozytorium:

```bash
git clone https://github.com/yourusername/kindle_dict.git
cd kindle_dict
```

2. Skopiuj plik `.env.example` na `.env` i dostosuj ustawienia:

```bash
cp .env.example .env
```

3. Umieść plik `kindlegen.exe` w katalogu `src/tools/`

4. Uruchom aplikację w trybie deweloperskim:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

5. Utwórz superużytkownika Django:

```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

6. Aplikacja powinna być dostępna pod adresem http://localhost:8000

## Struktura projektu

```
kindle_dict/
├── docker/                  # Pliki Dockerfile
├── src/                     # Kod źródłowy Django
│   ├── dictionary/          # Aplikacja do obsługi słowników
│   ├── kindle_dict/         # Główny moduł projektu
│   ├── media/               # Przesłane i wygenerowane pliki
│   ├── static/              # Pliki statyczne
│   ├── templates/           # Szablony HTML
│   └── tools/               # Narzędzia zewnętrzne (np. kindlegen.exe)
├── docker-compose.dev.yml   # Konfiguracja Docker dla rozwoju
├── docker-compose.prod.yml  # Konfiguracja Docker dla produkcji
└── .env                     # Zmienne środowiskowe
```

## Uruchamianie testów

```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py test
```

## Wdrożenie na produkcję

1. Dostosuj plik `.env` dla środowiska produkcyjnego
2. Uruchom z konfiguracją produkcyjną:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Wsparcie techniczne

W przypadku problemów, proszę o kontakt [email@example.com](mailto:email@example.com).