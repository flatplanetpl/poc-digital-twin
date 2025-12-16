# Konfiguracja

Kompletny przewodnik po wszystkich opcjach konfiguracyjnych Digital Twin.

---

## Spis treści

1. [Plik .env — przegląd](#plik-env--przegląd)
2. [Konfiguracja ścieżek](#konfiguracja-ścieżek)
3. [Tryb offline (FR-P0-2)](#tryb-offline-fr-p0-2)
4. [Baza wektorowa Qdrant](#baza-wektorowa-qdrant)
5. [Model embeddingów](#model-embeddingów)
6. [Dostawcy LLM](#dostawcy-llm)
7. [Parametry RAG](#parametry-rag)
8. [Priorytety dokumentów (FR-P0-3)](#priorytety-dokumentów-fr-p0-3)
9. [Audyt i logowanie](#audyt-i-logowanie)
10. [Przykładowe konfiguracje](#przykładowe-konfiguracje)

---

## Plik .env — przegląd

Wszystkie ustawienia są zdefiniowane w pliku `.env` w głównym katalogu projektu. System używa Pydantic Settings, więc możesz również ustawiać wartości przez zmienne środowiskowe.

```bash
# Skopiuj przykład
cp .env.example .env

# Edytuj
nano .env
```

**Priorytet konfiguracji:**
1. Zmienne środowiskowe systemu (najwyższy)
2. Plik `.env`
3. Wartości domyślne w kodzie (najniższy)

---

## Konfiguracja ścieżek

```bash
# Katalog z danymi do zindeksowania
DATA_DIR=./data

# Katalog na bazy danych i cache
STORAGE_DIR=./storage
```

**Struktura katalogów:**

```
digital-twin/
├── data/                    # DATA_DIR
│   ├── notes/               # Notatki .txt, .md
│   ├── emails/              # E-maile .eml, .mbox
│   ├── whatsapp/            # Eksporty WhatsApp
│   └── messenger/           # Eksporty Messenger JSON
│
├── storage/                 # STORAGE_DIR
│   ├── chat_history.db      # Historia konwersacji (SQLite)
│   ├── document_registry.db # Rejestr dokumentów (SQLite)
│   └── audit.db             # Log audytu (SQLite)
```

**Ścieżki absolutne vs względne:**

```bash
# Względne (zalecane dla portability)
DATA_DIR=./data

# Absolutne (dla specyficznych deploymentów)
DATA_DIR=/home/user/documents/digital-twin-data
```

---

## Tryb offline (FR-P0-2)

Tryb offline zapewnia, że **żadne dane nie opuszczają Twojego komputera**.

```bash
# Włącz pełny tryb offline
OFFLINE_MODE=true

# Lub: zezwól na lokalne, ale zablokuj chmurowe LLM
OFFLINE_MODE=false
ALLOW_CLOUD_LLM=false
```

### Macierz konfiguracji

| OFFLINE_MODE | ALLOW_CLOUD_LLM | Dostępne LLM | Dane wysyłane? |
|:------------:|:---------------:|--------------|:--------------:|
| `false` | `true` | gpt4all, openai, anthropic | Tak (jeśli wybierzesz cloud) |
| `false` | `false` | tylko gpt4all | Nie |
| `true` | `*` (ignorowane) | tylko gpt4all | Nie |

### Wymuszanie offline w kodzie

```python
from src.llm import create_llm, OfflineModeError

try:
    llm = create_llm("openai")  # Rzuci wyjątek w trybie offline
except OfflineModeError as e:
    print(f"Błokowane: {e}")
    llm = create_llm("gpt4all")  # Fallback
```

### Wskaźnik w UI

Gdy `OFFLINE_MODE=true`, w interfejsie Streamlit pojawi się ostrzeżenie:

```
⚠️ TRYB OFFLINE — Chmurowe LLM są wyłączone
```

---

## Baza wektorowa Qdrant

```bash
# Adres hosta Qdrant
QDRANT_HOST=localhost

# Port (domyślnie 6333)
QDRANT_PORT=6333

# Nazwa kolekcji (indeksu)
QDRANT_COLLECTION=digital_twin
```

### Konfiguracja Docker

W `docker-compose.yml`:

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"    # REST API
      - "6334:6334"    # gRPC (opcjonalnie)
    volumes:
      - ./qdrant_data:/qdrant/storage  # Persystencja
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

### Zdalna instancja Qdrant

Dla produkcji możesz użyć Qdrant Cloud lub własnego serwera:

```bash
QDRANT_HOST=your-instance.cloud.qdrant.io
QDRANT_PORT=6333
# Dodaj klucz API jeśli wymagany:
# QDRANT_API_KEY=your-api-key
```

### Wiele kolekcji

Możesz mieć osobne kolekcje dla różnych projektów:

```bash
# Projekt A
QDRANT_COLLECTION=project_a

# Projekt B (w osobnym .env lub zmiennej)
QDRANT_COLLECTION=project_b
```

---

## Model embeddingów

```bash
# Domyślny: szybki, kompaktowy
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Dostępne modele

| Model | Wymiary | Rozmiar | Języki | Użycie |
|-------|:-------:|:-------:|--------|--------|
| `all-MiniLM-L6-v2` | 384 | 90 MB | EN | Domyślny, szybki |
| `all-mpnet-base-v2` | 768 | 420 MB | EN | Większa dokładność |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 470 MB | 50+ | **Polski!** |
| `distiluse-base-multilingual-cased-v2` | 512 | 480 MB | 15 | Wielojęzyczny |

### Zalecenie dla polskiego

```bash
# Dla dokumentów po polsku:
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### Wpływ zmiany modelu

> ⚠️ **UWAGA**: Zmiana modelu embeddingów wymaga **pełnego re-indeksowania** wszystkich dokumentów!

```bash
# Po zmianie EMBEDDING_MODEL:
python scripts/ingest.py --source ./data/ --reset
```

---

## Dostawcy LLM

### GPT4All (lokalny, domyślny)

```bash
LLM_PROVIDER=gpt4all

# Model (pobierany automatycznie przy pierwszym użyciu)
GPT4ALL_MODEL=mistral-7b-instruct-v0.1.Q4_0.gguf
```

**Dostępne modele GPT4All:**

| Model | Rozmiar | RAM | Jakość | Szybkość |
|-------|:-------:|:---:|:------:|:--------:|
| `mistral-7b-instruct-v0.1.Q4_0.gguf` | 4.1 GB | 8 GB | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| `nous-hermes-llama2-13b.Q4_0.gguf` | 7.3 GB | 16 GB | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| `orca-mini-3b-gguf2-q4_0.gguf` | 1.8 GB | 4 GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `gpt4all-falcon-newbpe-q4_0.gguf` | 4.1 GB | 8 GB | ⭐⭐⭐⭐ | ⭐⭐⭐ |

### OpenAI

```bash
LLM_PROVIDER=openai

# Klucz API (uzyskaj na platform.openai.com)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Model
OPENAI_MODEL=gpt-4-turbo
# Alternatywy: gpt-4o, gpt-4o-mini, gpt-3.5-turbo
```

**Porównanie modeli OpenAI:**

| Model | Koszt (1M tokenów) | Jakość | Szybkość |
|-------|:------------------:|:------:|:--------:|
| `gpt-4-turbo` | $10 / $30 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| `gpt-4o` | $5 / $15 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `gpt-4o-mini` | $0.15 / $0.60 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `gpt-3.5-turbo` | $0.50 / $1.50 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Anthropic (Claude)

```bash
LLM_PROVIDER=anthropic

# Klucz API (uzyskaj na console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Model
ANTHROPIC_MODEL=claude-3-sonnet-20240229
# Alternatywy: claude-3-opus-20240229, claude-3-haiku-20240307
```

**Porównanie modeli Claude:**

| Model | Koszt (1M tokenów) | Jakość | Szybkość |
|-------|:------------------:|:------:|:--------:|
| `claude-3-opus` | $15 / $75 | ⭐⭐⭐⭐⭐+ | ⭐⭐ |
| `claude-3-sonnet` | $3 / $15 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `claude-3-haiku` | $0.25 / $1.25 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Parametry RAG

```bash
# Rozmiar fragmentu dokumentu (w znakach, ~4 znaki = 1 token)
CHUNK_SIZE=512

# Nakładanie się fragmentów (dla zachowania kontekstu)
CHUNK_OVERLAP=50

# Liczba dokumentów do pobrania przy wyszukiwaniu
TOP_K=5
```

### Dostrajanie parametrów

| Parametr | Mniejsza wartość | Większa wartość |
|----------|------------------|-----------------|
| `CHUNK_SIZE` | Precyzyjniejsze wyszukiwanie, więcej fragmentów | Więcej kontekstu w fragmencie, mniej precyzji |
| `CHUNK_OVERLAP` | Szybsze indeksowanie | Lepsze zachowanie kontekstu między fragmentami |
| `TOP_K` | Szybsze odpowiedzi, mniejszy kontekst | Więcej źródeł, pełniejsze odpowiedzi |

### Zalecane konfiguracje

```bash
# Krótkie dokumenty (notatki, czaty)
CHUNK_SIZE=256
CHUNK_OVERLAP=25
TOP_K=10

# Długie dokumenty (artykuły, raporty)
CHUNK_SIZE=1024
CHUNK_OVERLAP=100
TOP_K=5

# Balans (domyślne)
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K=5
```

---

## Priorytety dokumentów (FR-P0-3)

System waży dokumenty według ich ważności. Konfiguracja wag:

```bash
# Waga podobieństwa semantycznego (0.0 - 1.0)
PRIORITY_SIMILARITY_WEIGHT=0.7

# Waga priorytetu dokumentu (0.0 - 1.0)
PRIORITY_DOCUMENT_WEIGHT=0.3

# Maksymalny wiek dokumentu dla decay (dni)
PRIORITY_RECENCY_MAX_DAYS=365
```

### Formuła końcowa

```
final_score = PRIORITY_SIMILARITY_WEIGHT * similarity_score
            + PRIORITY_DOCUMENT_WEIGHT * priority_score
```

Gdzie `priority_score` = `type_score` + `approval_score` + `recency_score`

### Przykładowe konfiguracje

```bash
# Priorytetyzuj podobieństwo (tradycyjne RAG)
PRIORITY_SIMILARITY_WEIGHT=0.9
PRIORITY_DOCUMENT_WEIGHT=0.1

# Priorytetyzuj typ dokumentu (decyzje > notatki > czaty)
PRIORITY_SIMILARITY_WEIGHT=0.5
PRIORITY_DOCUMENT_WEIGHT=0.5

# Preferuj nowsze dokumenty
PRIORITY_RECENCY_MAX_DAYS=90  # 3 miesiące decay
```

Szczegóły: **[FR-P0-3: Priority Rules](FR-P0-3-Priority-Rules)**

---

## Audyt i logowanie

```bash
# Włącz logowanie operacji (index, delete, etc.)
AUDIT_ENABLED=true

# Loguj operacje zapytań (tylko metadane, NIE treść pytań)
AUDIT_QUERIES=false
```

### Co jest logowane?

| Operacja | Zapisywane dane | AUDIT_QUERIES |
|----------|-----------------|:-------------:|
| index | document_id, source_type, chunk_count | - |
| delete | document_id, reason | - |
| query | timestamp, document_ids użyte | Wymagane |
| export | format, count | - |

### Gdzie znajdują się logi?

```bash
# Baza SQLite
storage/audit.db

# Podgląd przez SQLite CLI
sqlite3 storage/audit.db "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;"
```

---

## Przykładowe konfiguracje

### Maksymalna prywatność

```bash
# Tylko lokalne przetwarzanie
OFFLINE_MODE=true
LLM_PROVIDER=gpt4all
GPT4ALL_MODEL=mistral-7b-instruct-v0.1.Q4_0.gguf

# Pełny audyt
AUDIT_ENABLED=true
AUDIT_QUERIES=true

# Krótki decay — preferuj świeże dokumenty
PRIORITY_RECENCY_MAX_DAYS=180
```

### Maksymalna jakość

```bash
# Najlepszy model chmurowy
OFFLINE_MODE=false
ALLOW_CLOUD_LLM=true
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-3-opus-20240229

# Więcej kontekstu
TOP_K=10
CHUNK_SIZE=1024

# Dokładniejsze embeddingi
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

### Niski koszt (produkcja)

```bash
# Tani model chmurowy
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# Mniejszy kontekst = mniej tokenów
TOP_K=3
CHUNK_SIZE=256

# Priorytetyzuj podobieństwo
PRIORITY_SIMILARITY_WEIGHT=0.85
PRIORITY_DOCUMENT_WEIGHT=0.15
```

### Polski — wielojęzyczny

```bash
# Model embeddingów wspierający polski
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Lub lokalny LLM dobry w polskim (jeśli dostępny)
# Alternatywnie: Claude 3 dobrze radzi sobie z polskim
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

---

## Walidacja konfiguracji

Sprawdź aktualną konfigurację w Pythonie:

```python
from src.config import settings

print(f"Data dir: {settings.data_dir}")
print(f"Offline: {settings.offline_mode}")
print(f"LLM: {settings.llm_provider}")
print(f"Available LLMs: {settings.available_llm_providers}")
print(f"Embedding: {settings.embedding_model}")
print(f"Priority weights: sim={settings.priority_similarity_weight}, doc={settings.priority_document_weight}")
```

---

<p align="center">
  <a href="Instalacja">← Instalacja</a> |
  <a href="Home">Strona główna</a> |
  <a href="Podstawy-użytkowania">Podstawy użytkowania →</a>
</p>
