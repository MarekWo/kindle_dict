# Skrypty pomocnicze dla Kindle Dictionary Creator

## process_kindlegen_jobs.py

Skrypt służący do przetwarzania zadań konwersji słowników do formatu MOBI poza kontenerem Docker.

### Problem

W kontenerze Docker występuje problem z uruchamianiem kindlegen.exe przez Wine w kontekście Celery. Błąd "privileged instruction in 32-bit code" wskazuje na problem z uprawnieniami lub konfiguracją środowiska wykonania.

### Rozwiązanie

Skrypt `process_kindlegen_jobs.py` monitoruje katalog `src/media/kindlegen_jobs` w poszukiwaniu nowych zadań konwersji, przetwarza je przy użyciu kindlegen na hoście (poza kontenerem Docker) i aktualizuje status zadania.

### Wymagania

- Python 3.6+
- Wine (na systemach Linux/macOS) lub natywny kindlegen.exe (na Windows)
- Dostęp do katalogu `src/media/kindlegen_jobs`

#### Instalacja Wine na Ubuntu/Debian (dla kindlegen.exe)

Kindlegen.exe jest aplikacją 32-bitową, więc wymaga zainstalowania wine32. Poniżej znajduje się procedura instalacji na Ubuntu/Debian:

1. Zainstaluj podstawową wersję Wine:
```bash
sudo apt install wine
```

2. Włącz obsługę architektury 32-bitowej:
```bash
sudo dpkg --add-architecture i386
```

3. Zaktualizuj repozytoria:
```bash
sudo apt update
```

4. Zainstaluj wine32:
```bash
sudo apt install wine32
```

5. Sprawdź instalację:
```bash
wine --version
```

**Uwaga**: Podczas uruchamiania kindlegen.exe z użyciem wine w interfejsie użytkownika, warto przekierować błędy standardowe do /dev/null, aby uniknąć komunikatów o błędach związanych z wyświetlaniem:

```bash
wine kindlegen.exe ksiazka.opf 2>/dev/null
```

W przypadku skryptu `process_kindlegen_jobs.py` działającego w tle, te komunikaty nie są widoczne i nie wpływają na działanie.

### Użycie

```bash
# Uruchomienie w trybie ciągłym (monitorowanie katalogu)
python scripts/process_kindlegen_jobs.py --media-root=./src/media --kindlegen-path=./src/tools/kindlegen.exe

# Uruchomienie w trybie jednorazowym (przetworzenie oczekujących zadań i zakończenie)
python scripts/process_kindlegen_jobs.py --media-root=./src/media --kindlegen-path=./src/tools/kindlegen.exe --one-shot
```

### Parametry

- `--media-root` - ścieżka do katalogu media (domyślnie: ./src/media)
- `--kindlegen-path` - ścieżka do pliku kindlegen.exe (domyślnie: ./src/tools/kindlegen.exe)
- `--interval` - interwał w sekundach między sprawdzeniami nowych zadań (domyślnie: 5)
- `--wine-path` - ścieżka do programu wine (domyślnie: wine)
- `--one-shot` - przetworzenie oczekujących zadań jednorazowo i zakończenie

### Jak to działa

1. Aplikacja Django/Celery tworzy zadanie konwersji w katalogu `src/media/kindlegen_jobs/{job_id}/`
2. W katalogu zadania umieszczane są wszystkie pliki potrzebne do konwersji oraz plik `job.json` ze statusem "pending"
3. Skrypt `process_kindlegen_jobs.py` wykrywa nowe zadanie i uruchamia kindlegen na hoście
4. Po zakończeniu konwersji, skrypt aktualizuje plik `job.json` ze statusem "completed" lub "failed"
5. Aplikacja Django/Celery odczytuje zaktualizowany status i kontynuuje przetwarzanie

### Przykład pliku job.json

```json
{
  "opf_file": "Diuna - Leksykon.opf",
  "output_file": "Diuna - Leksykon.mobi",
  "status": "pending",
  "created_at": 1710511234.567
}
```

Po przetworzeniu:

```json
{
  "opf_file": "Diuna - Leksykon.opf",
  "output_file": "Diuna - Leksykon.mobi",
  "status": "completed",
  "created_at": 1710511234.567,
  "updated_at": 1710511245.678
}
```

### Rozwiązywanie problemów

1. Upewnij się, że katalog `src/media/kindlegen_jobs` istnieje i ma odpowiednie uprawnienia
2. Sprawdź, czy kindlegen.exe jest dostępny pod podaną ścieżką
3. Na systemach Linux/macOS upewnij się, że Wine jest zainstalowany i działa poprawnie
4. Sprawdź logi skryptu w pliku `kindlegen_processor.log`
