# FAQ — Najczęstsze pytania

Odpowiedzi na najczęstsze pytania dotyczące Digital Twin.

---

## Spis treści

1. [Ogólne](#ogólne)
2. [Prywatność i bezpieczeństwo](#prywatność-i-bezpieczeństwo)
3. [Instalacja i konfiguracja](#instalacja-i-konfiguracja)
4. [Użytkowanie](#użytkowanie)
5. [Troubleshooting](#troubleshooting)
6. [Rozwój i roadmap](#rozwój-i-roadmap)

---

## Ogólne

### Co to jest Digital Twin?

Digital Twin to osobisty asystent AI, który przetwarza Twoje prywatne dane (notatki, e-maile, wiadomości) i odpowiada na pytania **wyłącznie na podstawie Twoich dokumentów**. W przeciwieństwie do ChatGPT czy Claude, Digital Twin:

- Może działać całkowicie offline
- Nigdy nie "halucynuje" — odpowiada tylko tym, co wie
- Zawsze cytuje źródła swoich odpowiedzi
- Daje pełną kontrolę nad danymi

### Czym różni się od ChatGPT/Claude?

| Aspekt | ChatGPT/Claude | Digital Twin |
|--------|---------------|--------------|
| Źródło wiedzy | Trening na internecie | **Twoje dokumenty** |
| Prywatność | Dane na serwerach firmy | **Lokalnie (opcja offline)** |
| Halucynacje | Częste | **Niemożliwe** (grounded) |
| Cytaty | Brak | **Obowiązkowe** |
| Kontrola danych | Brak | **Pełna** (RTBF) |

### Jakie formaty danych są obsługiwane?

**Obecnie (v1.0):**
- Notatki: `.txt`, `.md`
- E-maile: `.eml`, `.mbox`
- WhatsApp: `.txt` (eksport z aplikacji)
- Messenger: `.json` (eksport z Facebooka)

**Planowane:**
- PDF
- DOCX
- Obsidian vault
- Notion export

### Czy mogę używać po polsku?

Tak! Aby uzyskać lepsze wyniki po polsku:

1. Użyj wielojęzycznego modelu embeddingów:
   ```bash
   EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   ```

2. Rozważ Claude 3 lub GPT-4 (dobrze radzą sobie z polskim):
   ```bash
   LLM_PROVIDER=anthropic
   ANTHROPIC_MODEL=claude-3-sonnet-20240229
   ```

---

## Prywatność i bezpieczeństwo

### Czy moje dane są bezpieczne?

**W trybie offline (OFFLINE_MODE=true):**
- ✅ Wszystkie dane pozostają na Twoim komputerze
- ✅ Brak połączeń do zewnętrznych API
- ✅ Pełna kontrola

**W trybie online:**
- ⚠️ Fragmenty dokumentów są wysyłane do API (OpenAI/Anthropic)
- ⚠️ Tylko te fragmenty, które pasują do zapytania (nie cały indeks)
- ✅ Embedding jest lokalny (nigdy nie wysyłany)

### Czy OpenAI/Anthropic widzą moje dane?

Gdy używasz LLM chmurowych:
- **Tak** — fragmenty kontekstu są wysyłane do API
- **Nie** — cały indeks NIE jest wysyłany
- **Nie** — embeddingi są obliczane lokalnie

Rozwiązanie: Użyj `OFFLINE_MODE=true` dla wrażliwych danych.

### Jak całkowicie wyłączyć internet?

```bash
# 1. Tryb offline w konfiguracji
OFFLINE_MODE=true

# 2. Pobierz model wcześniej
mkdir -p ~/.cache/gpt4all
wget -O ~/.cache/gpt4all/mistral-7b-instruct-v0.1.Q4_0.gguf \
  https://gpt4all.io/models/gguf/mistral-7b-instruct-v0.1.Q4_0.gguf

# 3. Odłącz sieć (opcjonalnie)
nmcli networking off  # Linux
```

### Jak usunąć swoje dane? (RODO)

```python
from src.rag import ForgetService

forget = ForgetService(...)

# Usuń wszystko od nadawcy
result = forget.forget_sender("jan@example.com", "RODO request")

# Usuń konkretny dokument
result = forget.forget_document("uuid...", "User request")

# Usuń wszystkie dane typu
result = forget.forget_by_source_type("whatsapp", "Privacy cleanup")
```

### Czy jest logowanie?

Tak, ale **privacy-safe**:
- ✅ Logowane: ID dokumentów, typy operacji, timestampy
- ❌ NIE logowane: treść dokumentów, treść pytań

Konfiguracja:
```bash
AUDIT_ENABLED=true   # Włącz audyt
AUDIT_QUERIES=false  # NIE loguj zapytań
```

---

## Instalacja i konfiguracja

### Jakie są wymagania systemowe?

| Komponent | Minimum | Zalecane |
|-----------|---------|----------|
| RAM | 8 GB | 16 GB |
| Dysk | 10 GB | 50 GB SSD |
| Python | 3.10 | 3.11+ |
| Docker | 20.10+ | najnowszy |

### Dlaczego Qdrant przez Docker?

Qdrant to wyspecjalizowana baza wektorowa, która:
- Efektywnie przechowuje miliony wektorów
- Oferuje szybkie wyszukiwanie podobieństwa
- Wspiera filtry metadanych
- Jest production-ready

Docker upraszcza instalację i aktualizacje.

### Czy mogę użyć innej bazy wektorowej?

Teoretycznie tak (LlamaIndex wspiera wiele), ale:
- Qdrant jest zoptymalizowany i przetestowany
- Inne bazy mogą wymagać zmian w kodzie
- Brak oficjalnego wsparcia

### Jak zmienić model embeddingów?

1. Zmień w `.env`:
   ```bash
   EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
   ```

2. **WAŻNE:** Re-indeksuj wszystkie dokumenty:
   ```bash
   python scripts/ingest.py --source ./data/ --reset
   ```

### Jak używać GPU z GPT4All?

GPT4All automatycznie wykrywa GPU. Dla NVIDIA:

```bash
# Zainstaluj CUDA toolkit
# Skompiluj llama-cpp-python z CUDA:
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall
```

---

## Użytkowanie

### Jak eksportować dane z WhatsApp?

1. Otwórz WhatsApp na telefonie
2. Wejdź do rozmowy
3. Menu (⋮) → Więcej → Eksportuj czat
4. Wybierz "Bez multimediów"
5. Wyślij do siebie (email/cloud)
6. Zapisz `.txt` do `data/whatsapp/`

### Jak eksportować dane z Messenger?

1. Wejdź na facebook.com/dyi
2. Kliknij "Pobierz informacje"
3. Wybierz "Wiadomości" → Format JSON
4. Pobierz i rozpakuj
5. Skopiuj `message_*.json` do `data/messenger/`

### Dlaczego odpowiedzi są wolne?

Przyczyny:
1. **GPT4All na CPU** — lokalne modele są wolniejsze
2. **Duży kontekst** — więcej dokumentów = dłuższe przetwarzanie

Rozwiązania:
```bash
# Mniejszy model
GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf

# Mniej kontekstu
TOP_K=3

# Użyj GPU
# lub chmury (szybsza):
LLM_PROVIDER=openai
```

### Dlaczego nie znajduje dokumentu?

Możliwe przyczyny:

1. **Nie zindeksowany:**
   ```bash
   python scripts/ingest.py --stats
   # Sprawdź czy dokument jest w indeksie
   ```

2. **Złe słowa kluczowe:**
   ```python
   # Wyszukiwanie semantyczne ≠ keyword search
   # "umowa najmu" znajdzie "kontrakt wynajmu"
   ```

3. **Niski priorytet:**
   ```python
   # Dokumenty o niskim priorytecie mogą być pominięte
   # Sprawdź z include_explanation=True
   ```

### Jak przypinać ważne dokumenty?

```python
from src.indexer import VectorStore

vs = VectorStore()
vs.update_metadata(document_id, {"is_pinned": True})
```

Lub przez frontmatter w Markdown:
```markdown
---
is_pinned: true
category: decision
---

Treść dokumentu...
```

---

## Troubleshooting

### "Connection refused" do Qdrant

```bash
# Sprawdź czy Qdrant działa
docker ps | grep qdrant

# Restart
docker-compose down
docker-compose up -d

# Sprawdź logi
docker logs qdrant
```

### "OfflineModeError"

```bash
# Problem: próbujesz użyć OpenAI/Anthropic w trybie offline

# Rozwiązanie 1: Wyłącz offline
OFFLINE_MODE=false

# Rozwiązanie 2: Użyj lokalnego
LLM_PROVIDER=gpt4all
```

### "ModuleNotFoundError"

```bash
# Upewnij się, że środowisko jest aktywne
source .venv/bin/activate

# Reinstaluj
pip install -e .
```

### Brak cytatów w odpowiedzi

```python
# Sprawdź czy są dokumenty
result = engine.query("test", include_explanation=True)
print(len(result["explanation"]["documents_retrieved"]))

# Jeśli 0 — problem z indeksem lub zapytaniem
# Jeśli >0 — problem z LLM (ignoruje prompt)
```

### "CUDA out of memory"

```bash
# Mniejszy model
GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf

# Lub wymuś CPU (w kodzie):
# GPT4All(model_name, device='cpu')
```

### Streamlit nie startuje

```bash
# Sprawdź port
lsof -i :8501

# Użyj innego portu
streamlit run src/ui/app.py --server.port 8502
```

---

## Rozwój i roadmap

### Kiedy będzie wsparcie dla PDF?

PDF jest planowany w fazie P1 (następna wersja). Tymczasowo:

```bash
# Konwersja PDF → TXT
pdftotext dokument.pdf dokument.txt
mv dokument.txt data/notes/
```

### Czy mogę dodać własny loader?

Tak! Zobacz [Integracje → Własne loadery](Integracje#własne-loadery)

### Jak kontrybuować?

1. Fork repozytorium
2. Stwórz branch: `git checkout -b feature/moja-funkcja`
3. Commituj zmiany
4. Push i Pull Request

### Gdzie zgłaszać błędy?

[GitHub Issues](https://github.com/flatplanetpl/poc-digital-twin/issues)

### Czy będzie wersja SaaS?

Nie planujemy wersji chmurowej. Digital Twin jest projektem **privacy-first** — Twoje dane pozostają u Ciebie.

---

## Słownik pojęć

| Termin | Definicja |
|--------|-----------|
| **RAG** | Retrieval-Augmented Generation — technika łącząca wyszukiwanie z generowaniem |
| **Embedding** | Reprezentacja wektorowa tekstu umożliwiająca wyszukiwanie semantyczne |
| **Grounding** | Zakotwiczenie odpowiedzi w źródłach (przeciwieństwo halucynacji) |
| **RTBF** | Right To Be Forgotten — prawo do usunięcia danych (RODO) |
| **Chunking** | Podział dokumentu na mniejsze fragmenty do indeksowania |
| **Top-K** | Liczba najbardziej podobnych dokumentów do pobrania |
| **LLM** | Large Language Model — duży model językowy (GPT-4, Claude, etc.) |
| **Vector Store** | Baza danych przechowująca embeddingi (Qdrant) |

---

<p align="center">
  <a href="API-Reference">← API Reference</a> |
  <a href="Home">Strona główna</a>
</p>
