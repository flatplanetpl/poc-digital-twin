# Instalacja

Ten przewodnik przeprowadzi Cię przez pełną instalację Digital Twin — od zera do działającego systemu.

---

## Spis treści

1. [Wymagania systemowe](#wymagania-systemowe)
2. [Instalacja krok po kroku](#instalacja-krok-po-kroku)
3. [Weryfikacja instalacji](#weryfikacja-instalacji)
4. [Instalacja na różnych platformach](#instalacja-na-różnych-platformach)
5. [Rozwiązywanie problemów instalacyjnych](#rozwiązywanie-problemów-instalacyjnych)

---

## Wymagania systemowe

### Minimalne wymagania

| Komponent | Minimum | Zalecane |
|-----------|---------|----------|
| **CPU** | 4 rdzenie | 8+ rdzeni |
| **RAM** | 8 GB | 16 GB+ |
| **Dysk** | 10 GB wolnego | 50 GB+ SSD |
| **Python** | 3.10 | 3.11+ |
| **Docker** | 20.10+ | najnowszy |

### Wymagania dyskowe (szczegóły)

| Element | Rozmiar |
|---------|---------|
| Model GPT4All (Mistral 7B) | ~4 GB |
| Model embeddingów (MiniLM) | ~90 MB |
| Indeks Qdrant | ~1 MB / 1000 dokumentów |
| Baza SQLite | < 100 MB |
| Zależności Python | ~500 MB |

### Opcjonalne (dla GPU)

Jeśli chcesz przyspieszyć GPT4All przez GPU:
- **NVIDIA GPU**: CUDA 11.7+ (RTX 20xx lub nowsza)
- **AMD GPU**: ROCm 5.0+ (RX 6000 lub nowsza)
- **Apple Silicon**: Metal (M1/M2/M3 — natywne wsparcie)

---

## Instalacja krok po kroku

### Krok 1: Klonowanie repozytorium

```bash
# Przez SSH (zalecane)
git clone git@github.com:flatplanetpl/poc-digital-twin.git

# Lub przez HTTPS
git clone https://github.com/flatplanetpl/poc-digital-twin.git

# Przejdź do katalogu
cd poc-digital-twin
```

### Krok 2: Utworzenie środowiska wirtualnego

```bash
# Utwórz środowisko
python -m venv .venv

# Aktywuj (Linux/macOS)
source .venv/bin/activate

# Aktywuj (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Aktywuj (Windows CMD)
.venv\Scripts\activate.bat
```

> **Tip**: Dodaj aktywację do swojego `.bashrc` lub `.zshrc`:
> ```bash
> alias dt="cd ~/poc-digital-twin && source .venv/bin/activate"
> ```

### Krok 3: Instalacja zależności Python

```bash
# Podstawowa instalacja
pip install -e .

# Lub z zależnościami deweloperskimi
pip install -e ".[dev]"

# Weryfikacja
pip list | grep -E "llama|qdrant|streamlit"
```

**Oczekiwany output:**
```
llama-index                 0.10.x
llama-index-embeddings-huggingface 0.x.x
llama-index-vector-stores-qdrant   0.x.x
qdrant-client               1.x.x
streamlit                   1.x.x
```

### Krok 4: Uruchomienie Qdrant (Docker)

```bash
# Uruchom Qdrant w tle
docker-compose up -d

# Sprawdź status
docker ps

# Oczekiwany output:
# CONTAINER ID   IMAGE         COMMAND    STATUS         PORTS
# xxxxxxxxxxxx   qdrant/qdrant ...        Up 5 seconds   0.0.0.0:6333->6333/tcp
```

**Weryfikacja Qdrant:**
```bash
curl http://localhost:6333/health
# Oczekiwany output: {"status":"ok"}
```

### Krok 5: Konfiguracja środowiska

```bash
# Skopiuj przykładowy plik konfiguracji
cp .env.example .env

# Edytuj według potrzeb
nano .env  # lub vim, code, itp.
```

**Minimalna konfiguracja `.env`:**
```bash
# Ścieżki
DATA_DIR=./data
STORAGE_DIR=./storage

# LLM (lokalny)
LLM_PROVIDER=gpt4all
GPT4ALL_MODEL=mistral-7b-instruct-v0.1.Q4_0.gguf

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

Szczegóły: **[Konfiguracja](Konfiguracja)**

### Krok 6: Przygotowanie danych

```bash
# Utwórz strukturę katalogów
mkdir -p data/{notes,emails,whatsapp,messenger}

# Skopiuj swoje dane
cp ~/Documents/notes/*.md data/notes/
cp ~/Mail/Archive/*.eml data/emails/
# itd.
```

**Obsługiwane formaty:**

| Typ | Formaty | Katalog |
|-----|---------|---------|
| Notatki | `.txt`, `.md` | `data/notes/` |
| E-maile | `.eml`, `.mbox` | `data/emails/` |
| WhatsApp | `.txt` (eksport) | `data/whatsapp/` |
| Messenger | `.json` (eksport FB) | `data/messenger/` |

### Krok 7: Indeksowanie danych

```bash
# Pierwszy import (wszystkie typy)
python scripts/ingest.py --source ./data/

# Przykładowy output:
# Connecting to Qdrant...
# Loading data from: ./data
#   Loading text files...
#     Found 42 documents
#   Loading email files...
#     Found 156 documents
#   Loading whatsapp files...
#     Found 23 documents
# Indexing 221 documents...
# Successfully indexed 221 documents.
# Index now contains 1847 vectors.
```

### Krok 8: Uruchomienie interfejsu

```bash
streamlit run src/ui/app.py

# Output:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
# Network URL: http://192.168.x.x:8501
```

Otwórz przeglądarkę: **http://localhost:8501**

---

## Weryfikacja instalacji

### Test 1: Sprawdź komponenty

```bash
# Python
python --version  # Python 3.10+

# Qdrant
curl http://localhost:6333/health  # {"status":"ok"}

# Indeks
python scripts/ingest.py --stats
# Index Statistics:
#   Exists: True
#   Documents: 1847
#   Status: green
```

### Test 2: Proste zapytanie (Python)

```python
from src.rag import RAGEngine

engine = RAGEngine()
result = engine.query("Co mam w dokumentach?")
print(result["answer"])
print(f"Źródeł: {len(result['sources'])}")
```

### Test 3: Sprawdź tryb offline

```python
from src.config import settings
from src.llm import get_available_providers

print(f"Offline mode: {settings.offline_mode}")
print(f"Dostępne LLM: {get_available_providers()}")
```

---

## Instalacja na różnych platformach

### Ubuntu/Debian

```bash
# Zainstaluj wymagania systemowe
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip docker.io docker-compose

# Dodaj użytkownika do grupy docker
sudo usermod -aG docker $USER
newgrp docker

# Kontynuuj od Kroku 1
```

### macOS

```bash
# Zainstaluj Homebrew (jeśli brak)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Zainstaluj wymagania
brew install python@3.11 docker docker-compose

# Uruchom Docker Desktop
open -a Docker

# Kontynuuj od Kroku 1
```

### Windows (WSL2)

```powershell
# 1. Zainstaluj WSL2
wsl --install -d Ubuntu-22.04

# 2. W Ubuntu (WSL2):
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# 3. Zainstaluj Docker Desktop for Windows
# https://docs.docker.com/desktop/install/windows-install/

# 4. W Docker Desktop: Settings > Resources > WSL Integration > Enable Ubuntu

# 5. Kontynuuj od Kroku 1 w terminalu WSL
```

### Windows (natywnie)

```powershell
# 1. Zainstaluj Python z python.org
# https://www.python.org/downloads/

# 2. Zainstaluj Docker Desktop
# https://docs.docker.com/desktop/install/windows-install/

# 3. W PowerShell:
git clone https://github.com/flatplanetpl/poc-digital-twin.git
cd poc-digital-twin
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

# 4. Uruchom Docker Desktop, potem:
docker-compose up -d

# 5. Kontynuuj od Kroku 5
```

### Raspberry Pi (ARM64)

```bash
# Wymaga: Raspberry Pi 4 z 8GB RAM, 64-bit OS

# Zainstaluj wymagania
sudo apt update
sudo apt install -y python3.11 python3.11-venv docker.io

# UWAGA: GPT4All może być wolny na ARM
# Rozważ użycie mniejszego modelu lub API cloud

# Kontynuuj od Kroku 1
```

---

## Rozwiązywanie problemów instalacyjnych

### Problem: "Docker: command not found"

```bash
# Linux
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER
# Wyloguj się i zaloguj ponownie

# macOS
brew install docker docker-compose
# Lub zainstaluj Docker Desktop
```

### Problem: "Permission denied" przy docker

```bash
sudo usermod -aG docker $USER
newgrp docker
# Lub przeloguj się
```

### Problem: "Port 6333 already in use"

```bash
# Znajdź proces
sudo lsof -i :6333

# Zabij proces lub zmień port w .env:
QDRANT_PORT=6334

# I w docker-compose.yml:
ports:
  - "6334:6333"
```

### Problem: "ModuleNotFoundError: llama_index"

```bash
# Upewnij się, że środowisko jest aktywne
source .venv/bin/activate

# Reinstaluj
pip install -e .
```

### Problem: "CUDA out of memory" (GPU)

```bash
# Użyj mniejszego modelu
GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf

# Lub wymuś CPU
# W kodzie: model = GPT4All(model_name, device='cpu')
```

### Problem: Wolne pobieranie modelu GPT4All

Model (~4GB) jest pobierany przy pierwszym uruchomieniu. Możesz go pobrać ręcznie:

```bash
mkdir -p ~/.cache/gpt4all
wget -O ~/.cache/gpt4all/mistral-7b-instruct-v0.1.Q4_0.gguf \
  https://gpt4all.io/models/gguf/mistral-7b-instruct-v0.1.Q4_0.gguf
```

### Problem: "Connection refused" do Qdrant

```bash
# Sprawdź czy kontener działa
docker ps | grep qdrant

# Restart kontenera
docker-compose down
docker-compose up -d

# Sprawdź logi
docker logs qdrant
```

---

## Co dalej?

Po udanej instalacji:

1. **[Konfiguracja](Konfiguracja)** — dostosuj system do swoich potrzeb
2. **[Podstawy użytkowania](Podstawy-użytkowania)** — naucz się zadawać pytania
3. **[Scenariusze użycia](Scenariusze-użycia)** — inspiracje jak wykorzystać system

---

<p align="center">
  <a href="Home">← Powrót do strony głównej</a> |
  <a href="Konfiguracja">Konfiguracja →</a>
</p>
