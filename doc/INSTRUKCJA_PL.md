# Digital Twin — Instrukcja Obsługi

**Wersja:** 1.0 (P0 Critical)
**Język:** Polski
**Ostatnia aktualizacja:** Grudzień 2024

---

## Spis treści

1. [Wprowadzenie](#1-wprowadzenie)
2. [Instalacja](#2-instalacja)
3. [Konfiguracja](#3-konfiguracja)
4. [Podstawy użytkowania](#4-podstawy-użytkowania)
5. [Funkcje P0 Critical](#5-funkcje-p0-critical)
6. [Pipeline'y przetwarzania](#6-pipeliney-przetwarzania)
7. [Scenariusze użycia](#7-scenariusze-użycia)
8. [Integracje i rozszerzenia](#8-integracje-i-rozszerzenia)
9. [API Reference](#9-api-reference)
10. [FAQ i rozwiązywanie problemów](#10-faq-i-rozwiązywanie-problemów)

---

## 1. Wprowadzenie

### Czym jest Digital Twin?

**Digital Twin** to osobisty asystent AI, który przetwarza Twoje dane (notatki, e-maile, wiadomości z WhatsApp i Messengera) i odpowiada na pytania **wyłącznie na podstawie Twoich danych**. To jak posiadanie własnego "cyfrowego bliźniaka" — systemu, który zna Twoje dokumenty, decyzje i komunikację, ale **nigdy nie wysyła danych do chmury bez Twojej zgody**.

### Dlaczego prywatność ma znaczenie?

W erze AI większość narzędzi wymaga przesyłania danych do serwerów zewnętrznych. Digital Twin działa inaczej:

| Tradycyjne AI | Digital Twin |
|---------------|--------------|
| Dane wysyłane do chmury | Przetwarzanie lokalne (GPT4All) |
| Brak kontroli nad danymi | Pełna kontrola — możesz usunąć wszystko |
| Odpowiedzi z "wiedzy ogólnej" | Odpowiedzi **tylko** z Twoich dokumentów |
| Brak wyjaśnień | Pełna przejrzystość — widzisz skąd pochodzi odpowiedź |

### Kluczowe funkcje (P0 Critical)

| Funkcja | Opis |
|---------|------|
| **Grounded Answers** | Odpowiedzi tylko z Twoich danych + cytaty |
| **Offline Mode** | Praca bez internetu |
| **Priority Rules** | Ważniejsze dokumenty mają wyższy priorytet |
| **Explainability** | Widzisz dokładnie, które fragmenty zostały użyte |
| **Forget/RTBF** | Prawo do bycia zapomnianym — usuń dane gdy chcesz |

---

## 2. Instalacja

### Wymagania systemowe

- **Python:** 3.10+
- **Docker:** Do uruchomienia Qdrant (bazy wektorowej)
- **RAM:** Minimum 8 GB (16 GB zalecane dla GPT4All)
- **Dysk:** ~5 GB na model GPT4All + miejsce na dokumenty

### Krok po kroku

#### 2.1. Klonowanie repozytorium

```bash
git clone <repository-url>
cd digital-twin
```

#### 2.2. Utworzenie środowiska wirtualnego

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# lub: .venv\Scripts\activate  # Windows
```

#### 2.3. Instalacja zależności

```bash
pip install -e .
```

#### 2.4. Uruchomienie Qdrant (baza wektorowa)

```bash
docker-compose up -d
```

Sprawdzenie statusu:
```bash
docker ps
# Powinien być widoczny kontener "qdrant"
```

#### 2.5. Konfiguracja środowiska

```bash
cp .env.example .env
# Edytuj .env według potrzeb (szczegóły w sekcji 3)
```

#### 2.6. Pierwszy import danych

```bash
python scripts/ingest.py --source ./data/
```

#### 2.7. Uruchomienie interfejsu

```bash
streamlit run src/ui/app.py
```

Aplikacja będzie dostępna pod: `http://localhost:8501`

---

## 3. Konfiguracja

Wszystkie ustawienia znajdują się w pliku `.env`. Poniżej kompletny opis opcji.

### 3.1. Ścieżki

```bash
# Katalog z danymi do zindeksowania
DATA_DIR=./data

# Katalog na bazy danych (SQLite, cache)
STORAGE_DIR=./storage
```

### 3.2. Tryb offline (FR-P0-2)

```bash
# Włącz tryb offline — tylko lokalne LLM
OFFLINE_MODE=false

# Zezwól na chmurowe LLM (OpenAI, Anthropic)
ALLOW_CLOUD_LLM=true
```

**Kombinacje:**

| OFFLINE_MODE | ALLOW_CLOUD_LLM | Dostępne LLM |
|--------------|-----------------|--------------|
| false | true | gpt4all, openai, anthropic |
| false | false | tylko gpt4all |
| true | * | tylko gpt4all |

### 3.3. Baza wektorowa (Qdrant)

```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=digital_twin
```

### 3.4. Model embeddingów

```bash
# Model HuggingFace do wektoryzacji tekstu
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Inne opcje:
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` — wielojęzyczny
- `sentence-transformers/all-mpnet-base-v2` — większy, dokładniejszy

### 3.5. Dostawca LLM

```bash
# Domyślny dostawca: gpt4all | openai | anthropic
LLM_PROVIDER=gpt4all

# Model GPT4All (lokalny)
GPT4ALL_MODEL=mistral-7b-instruct-v0.1.Q4_0.gguf

# OpenAI (wymaga klucza API)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo

# Anthropic (wymaga klucza API)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

### 3.6. Parametry RAG

```bash
# Rozmiar fragmentu dokumentu (w tokenach)
CHUNK_SIZE=512

# Nakładanie się fragmentów
CHUNK_OVERLAP=50

# Liczba dokumentów do pobrania przy wyszukiwaniu
TOP_K=5
```

### 3.7. Priorytety dokumentów (FR-P0-3)

```bash
# Waga podobieństwa semantycznego (0-1)
PRIORITY_SIMILARITY_WEIGHT=0.7

# Waga priorytetu dokumentu (0-1)
PRIORITY_DOCUMENT_WEIGHT=0.3

# Maksymalny wiek dokumentu dla decay (dni)
PRIORITY_RECENCY_MAX_DAYS=365
```

### 3.8. Audyt (FR-P3-3)

```bash
# Włącz logowanie operacji
AUDIT_ENABLED=true

# Loguj operacje zapytań (tylko metadane, nie treść)
AUDIT_QUERIES=false
```

---

## 4. Podstawy użytkowania

### 4.1. Import danych

#### Struktura katalogów

```
data/
├── notes/           # Notatki (.txt, .md)
├── emails/          # E-maile (.eml, .mbox)
├── whatsapp/        # Eksporty WhatsApp (.txt)
└── messenger/       # Eksporty Messenger (.json)
```

#### Polecenie importu

```bash
# Import wszystkich typów
python scripts/ingest.py --source ./data/

# Import tylko notatek
python scripts/ingest.py --source ./data/ --types text

# Import z resetem indeksu
python scripts/ingest.py --source ./data/ --reset

# Sprawdzenie statystyk
python scripts/ingest.py --stats
```

### 4.2. Zadawanie pytań

#### Przez interfejs Streamlit

1. Otwórz `http://localhost:8501`
2. Wpisz pytanie w pole tekstowe
3. Kliknij "Wyślij" lub naciśnij Enter
4. Przeczytaj odpowiedź wraz z cytatami

#### Przez Python (programowo)

```python
from src.rag import RAGEngine

engine = RAGEngine()

# Proste zapytanie
result = engine.query("O czym pisałem w ostatnim mailu do Marka?")
print(result["answer"])
print(result["sources"])

# Zapytanie z wyjaśnieniem (FR-P0-4)
result = engine.query(
    "Jakie decyzje podjąłem w sprawie projektu X?",
    include_explanation=True
)
print(result["explanation"])

# Wyszukiwanie bez generowania odpowiedzi
docs = engine.search("umowa", top_k=10, source_type="email")
for doc in docs:
    print(f"{doc['filename']}: {doc['content'][:100]}...")
```

### 4.3. Zarządzanie konwersacjami

```python
from src.storage import ChatHistory

history = ChatHistory()

# Rozpocznij nową konwersację
conv_id = history.create_conversation("Projekt X")

# Zapytanie w kontekście konwersacji
result = engine.query(
    "A co z budżetem?",
    conversation_id=conv_id
)

# Pobierz historię konwersacji
messages = history.get_messages(conv_id)
```

---

## 5. Funkcje P0 Critical

### 5.1. Grounded Answers (FR-P0-1)

**Problem:** Tradycyjne LLM "halucynują" — wymyślają fakty, które brzmią wiarygodnie.

**Rozwiązanie:** Digital Twin odpowiada **wyłącznie** na podstawie zindeksowanych dokumentów i **zawsze** podaje źródło.

#### Jak to działa?

System używa specjalnego promptu:

```
Jesteś osobistym asystentem danych. Odpowiadaj TYLKO na podstawie kontekstu.

KRYTYCZNE ZASADY:
1. Używaj WYŁĄCZNIE informacji z kontekstu poniżej
2. Jeśli nie znaleziono: "Nie mogłem znaleźć tej informacji w Twoich danych."
3. NIGDY nie używaj wiedzy z treningu
4. ZAWSZE cytuj: [Źródło: {typ}, {data}, "{fragment}"]
```

#### Przykład odpowiedzi

**Pytanie:** "Kiedy umówiłem się z Anną na kawę?"

**Odpowiedź:**
```
Zgodnie z Twoimi wiadomościami, umówiłeś się z Anną na kawę
w piątek 15 grudnia o 14:00 w kawiarni "Pod Lipą".

[Źródło: whatsapp, 2024-12-10, "Ok, to w piątek o 14, Pod Lipą?"]
[Źródło: whatsapp, 2024-12-10, "Super, do zobaczenia!"]
```

#### Struktura cytatu

```python
@dataclass
class Citation:
    document_id: str      # UUID dokumentu
    source_type: str      # email, note, whatsapp, messenger
    filename: str         # Nazwa pliku
    date: str             # Data dokumentu
    fragment: str         # Cytowany fragment (do 100 znaków)
    score: float          # Wynik podobieństwa (0-1)
```

#### Sprawdzanie uziemienia

```python
result = engine.query("...")

if result["is_grounded"]:
    print("Odpowiedź oparta na dokumentach")
else:
    print("UWAGA: Odpowiedź może zawierać treści spoza kontekstu")

if result["no_context_found"]:
    print("Nie znaleziono pasujących dokumentów")
```

### 5.2. Offline Mode (FR-P0-2)

**Problem:** Wrażliwe dane osobiste nie powinny być wysyłane do serwerów zewnętrznych.

**Rozwiązanie:** Tryb offline wymusza użycie wyłącznie lokalnego modelu GPT4All.

#### Włączenie trybu offline

W `.env`:
```bash
OFFLINE_MODE=true
```

Lub dynamicznie:
```python
from src.config import settings

# Sprawdź aktualny tryb
print(f"Offline: {settings.is_offline}")
print(f"Dostępne LLM: {settings.available_llm_providers}")
```

#### Obsługa błędów

```python
from src.llm import create_llm, OfflineModeError

try:
    # Próba użycia OpenAI w trybie offline
    llm = create_llm("openai")
except OfflineModeError as e:
    print(f"Błąd: {e}")
    # "Cannot use cloud LLM 'openai' in offline mode"
```

#### Kiedy używać trybu offline?

| Scenariusz | Zalecane |
|------------|----------|
| Praca z danymi poufnymi | OFFLINE_MODE=true |
| Dane medyczne/prawne | OFFLINE_MODE=true |
| Normalna praca, szybkość ważna | OFFLINE_MODE=false, LLM_PROVIDER=openai |
| Demonstracja bez internetu | OFFLINE_MODE=true |

### 5.3. Priority Rules (FR-P0-3)

**Problem:** Nie wszystkie dokumenty są równie ważne. Formalna decyzja powinna mieć wyższą wagę niż losowy czat.

**Rozwiązanie:** System wagowy uwzględniający typ dokumentu, aktualność i status zatwierdzenia.

#### Hierarchia typów dokumentów

| Typ | Waga | Przykłady |
|-----|------|-----------|
| DECISION (100) | Najwyższa | Formalne decyzje, umowy |
| NOTE (70) | Wysoka | Osobiste notatki |
| EMAIL (50) | Średnia | Korespondencja |
| CONVERSATION (30) | Niska | WhatsApp, Messenger |

#### Status zatwierdzenia

| Status | Bonus | Opis |
|--------|-------|------|
| PINNED (+50) | Przypięty | Użytkownik oznaczył jako kluczowy |
| APPROVED (+30) | Zatwierdzony | Zweryfikowany przez użytkownika |
| AUTOMATIC (0) | Automatyczny | Domyślny status |

#### Formuła priorytetu

```
priority = type_score + approval_score + recency_score
final_score = 0.7 * similarity + 0.3 * priority
```

**Recency score** — nowsze dokumenty mają wyższą wagę (decay przez 365 dni):

```python
days_old = (now - doc_date).days
recency_score = max(0, 1 - (days_old / 365))
```

#### Przykład użycia

```python
from src.rag.priority import calculate_priority, DocumentType

# Oblicz priorytet dokumentu
priority = calculate_priority(
    source_type="email",
    date="2024-12-01",
    is_pinned=False,
    is_approved=True
)
print(f"Priorytet: {priority.priority_score}")
# type: 50 + approval: 30 + recency: ~0.96 = ~80.96

# Wyszukiwanie z priorytetami
from src.indexer import VectorStore

vs = VectorStore()
results = vs.search_with_priority(
    query="umowa",
    top_k=5,
    fetch_k=50  # Pobierz więcej, przefiltruj
)
```

### 5.4. Explainability (FR-P0-4)

**Problem:** "Czarna skrzynka" — nie wiadomo, dlaczego system wybrał dane dokumenty.

**Rozwiązanie:** Pełna transparentność — wyjaśnienie każdego kroku RAG.

#### Włączenie wyjaśnień

```python
result = engine.query(
    "Jakie mam zadania na ten tydzień?",
    include_explanation=True
)

explanation = result["explanation"]
```

#### Struktura wyjaśnienia

```python
@dataclass
class RAGExplanation:
    # Informacje o zapytaniu
    query_text: str
    query_embedding_model: str

    # Parametry wyszukiwania
    retrieval_mode: str      # "similarity", "priority_weighted"
    retrieval_top_k: int

    # Wyjaśnienia dla każdego dokumentu
    documents_retrieved: list[RetrievalExplanation]

    # Okno kontekstowe
    context_window: ContextWindowExplanation

    # Informacje o LLM
    response_mode: str       # "compact", "refine"
    llm_provider: str
    llm_model: str

    # Timing
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
```

#### Wyjaśnienie pojedynczego dokumentu

```python
@dataclass
class RetrievalExplanation:
    document_id: str
    filename: str
    source_type: str

    # Rozbicie scoringu
    similarity_score: float    # Podobieństwo wektorowe
    priority_score: float      # Priorytet dokumentu
    final_score: float         # Wynik końcowy

    # Składniki priorytetu
    type_contribution: float   # Z typu dokumentu
    recency_contribution: float # Z aktualności
    approval_contribution: float # Ze statusu

    rank: int  # Pozycja w rankingu
```

#### Przykład wyświetlenia

```python
explanation = result["explanation"]

print(f"Zapytanie przetworzone w {explanation['timing']['total_ms']:.0f}ms")
print(f"  Retrieval: {explanation['timing']['retrieval_ms']:.0f}ms")
print(f"  Generation: {explanation['timing']['generation_ms']:.0f}ms")

print(f"\nPobrano {len(explanation['documents_retrieved'])} dokumentów:")
for doc in explanation["documents_retrieved"]:
    print(f"  {doc['rank']}. {doc['filename']}")
    print(f"     Podobieństwo: {doc['similarity_score']:.2f}")
    print(f"     Priorytet: {doc['priority_score']:.2f}")
    print(f"     Wynik końcowy: {doc['final_score']:.2f}")
```

### 5.5. Forget / RTBF (FR-P0-5)

**Problem:** RODO wymaga "prawa do bycia zapomnianym" — możliwości usunięcia swoich danych.

**Rozwiązanie:** Kompletne usuwanie danych ze wszystkich systemów.

#### Usuwanie dokumentu

```python
from src.rag import ForgetService
from src.indexer import VectorStore
from src.storage import ChatHistory, DocumentRegistry

forget = ForgetService(
    vector_store=VectorStore(),
    chat_history=ChatHistory(),
    document_registry=DocumentRegistry()
)

# Usuń pojedynczy dokument
result = forget.forget_document(
    document_id="550e8400-e29b-41d4-a716-446655440000",
    reason="Życzenie użytkownika"
)

print(f"Usunięto:")
print(f"  Wektory: {result.vectors_deleted}")
print(f"  Referencje w historii: {result.references_deleted}")
print(f"  Dokumenty w rejestrze: {result.documents_deleted}")
```

#### Usuwanie po nadawcy

```python
# Usuń wszystkie wiadomości od konkretnej osoby
result = forget.forget_sender(
    sender="jan.kowalski@example.com",
    reason="RODO - żądanie usunięcia"
)
```

#### Usuwanie po typie źródła

```python
# Usuń wszystkie czaty WhatsApp
result = forget.forget_by_source_type(
    source_type="whatsapp",
    reason="Rezygnacja z synchronizacji"
)
```

#### Co jest usuwane?

| Komponent | Co usuwane |
|-----------|------------|
| VectorStore (Qdrant) | Wektory embeddingów |
| ChatHistory (SQLite) | Referencje do źródeł w odpowiedziach |
| DocumentRegistry | Status dokumentu → "deleted" |
| AuditLog | Wpis o operacji usunięcia (bez treści) |

#### Audyt operacji usuwania

```python
from src.storage import AuditLogger

audit = AuditLogger()

# Wyświetl ostatnie operacje usuwania
entries = audit.get_entries(
    operation_type="delete",
    limit=10
)

for entry in entries:
    print(f"{entry.timestamp}: Usunięto {entry.entity_id}")
    print(f"  Powód: {entry.details.get('reason')}")
```

---

## 6. Pipeline'y przetwarzania

### 6.1. Pipeline indeksowania

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Pliki     │ ──► │   Loader    │ ──► │   Chunker   │
│ (txt,eml...)│     │ (parsowanie)│     │ (512 tok.)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Qdrant    │ ◄── │  Embedding  │ ◄── │  Metadata   │
│ (wektory)   │     │ (MiniLM)    │     │ (UUID, typ) │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Registry   │
                                        │  (SQLite)   │
                                        └─────────────┘
```

**Kroki:**
1. **Loader** — rozpoznaje typ pliku, parsuje treść
2. **Chunker** — dzieli na fragmenty 512 tokenów z 50 overlap
3. **Metadata** — dodaje UUID, typ, datę, kategorię
4. **Embedding** — wektoryzuje przez all-MiniLM-L6-v2
5. **Qdrant** — zapisuje wektory z metadanymi
6. **Registry** — rejestruje dokument z hashem zawartości

### 6.2. Pipeline zapytania

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Pytanie    │ ──► │  Embedding  │ ──► │   Qdrant    │
│ użytkownika │     │ (MiniLM)    │     │  (search)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Priority   │ ──► │   Context   │ ──► │    LLM      │
│  Ranking    │     │  Building   │     │ (GPT4All)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Citation   │ ──► │ Grounding   │ ──► │  Odpowiedź  │
│ Extraction  │     │ Validation  │     │ + cytaty    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Kroki:**
1. **Embedding** — wektoryzacja pytania
2. **Search** — wyszukiwanie top_k najbardziej podobnych
3. **Priority Ranking** — przeliczenie z wagami priorytetów
4. **Context Building** — złożenie kontekstu z fragmentów
5. **LLM Generation** — wygenerowanie odpowiedzi
6. **Citation Extraction** — wyciągnięcie cytatów
7. **Grounding Validation** — sprawdzenie czy odpowiedź jest uziemiona

### 6.3. Pipeline usuwania (Forget)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Żądanie   │ ──► │   Lookup    │ ──► │   Delete    │
│  usunięcia  │     │ (registry)  │     │  (Qdrant)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Purge     │ ──► │   Update    │ ──► │   Audit     │
│ (history)   │     │ (registry)  │     │   Log       │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Kroki:**
1. **Lookup** — znajdź dokument(y) w rejestrze
2. **Delete Qdrant** — usuń wektory z bazy
3. **Purge History** — usuń referencje z historii czatów
4. **Update Registry** — oznacz jako "deleted"
5. **Audit Log** — zaloguj operację (bez treści)

---

## 7. Scenariusze użycia

### 7.1. Scenariusz: Przygotowanie do spotkania

**Sytuacja:** Masz spotkanie z klientem za godzinę. Chcesz przypomnieć sobie wszystkie ustalenia.

```python
# 1. Znajdź wszystkie komunikacje z klientem
docs = engine.search(
    "Acme Corp",
    top_k=20,
    source_type="email"
)

# 2. Zapytaj o kluczowe ustalenia
result = engine.query(
    "Jakie są najważniejsze ustalenia z moich rozmów z Acme Corp?",
    include_explanation=True
)

print(result["answer"])

# 3. Sprawdź chronologię
result = engine.query(
    "Przedstaw chronologię mojej komunikacji z Acme Corp"
)
```

**Przykładowa odpowiedź:**
```
Na podstawie Twoich dokumentów, kluczowe ustalenia z Acme Corp:

1. Budżet projektu: 150,000 PLN (zatwierdzone 2024-11-15)
   [Źródło: email, 2024-11-15, "Budżet zatwierdzony..."]

2. Deadline: 31 marca 2025
   [Źródło: email, 2024-11-20, "Termin końcowy..."]

3. Zespół: 3 programistów + 1 PM
   [Źródło: note, 2024-11-22, "Skład zespołu..."]
```

### 7.2. Scenariusz: Analiza własnych decyzji

**Sytuacja:** Chcesz zrozumieć, jak Twoje decyzje zmieniały się w czasie.

```python
# 1. Włącz priorytetyzację decyzji
from src.indexer import VectorStore

vs = VectorStore()

# 2. Zapytaj o decyzje w danym temacie
result = engine.query(
    "Jakie decyzje podejmowałem w sprawie inwestowania?",
    include_explanation=True
)

# 3. Sprawdź wyjaśnienie — które dokumenty zostały użyte
for doc in result["explanation"]["documents_retrieved"]:
    if doc["source_type"] == "note":
        print(f"Decyzja z {doc['filename']}: priorytet {doc['priority_score']:.2f}")
```

### 7.3. Scenariusz: Przypomnienie o zobowiązaniach

**Sytuacja:** Chcesz sprawdzić, co obiecałeś różnym osobom.

```python
# Znajdź zobowiązania
result = engine.query(
    "Jakie zobowiązania podjąłem w ostatnich 30 dniach?"
)

# Filtruj po nadawcy
result = engine.query(
    "Co obiecałem Ani w naszych rozmowach?"
)
```

### 7.4. Scenariusz: Praca offline z wrażliwymi danymi

**Sytuacja:** Przeglądasz dokumenty prawne i nie chcesz, żeby dane opuszczały komputer.

```python
# 1. Ustaw tryb offline
import os
os.environ["OFFLINE_MODE"] = "true"

# 2. Reload konfiguracji
from src.config import Settings
settings = Settings()

# 3. Sprawdź
print(f"Offline: {settings.is_offline}")
print(f"Dostępne LLM: {settings.available_llm_providers}")
# Output: Dostępne LLM: ['gpt4all']

# 4. Pracuj bezpiecznie
result = engine.query(
    "Jakie są kluczowe punkty umowy najmu?",
    include_explanation=True
)
```

### 7.5. Scenariusz: Usunięcie danych po zakończeniu współpracy

**Sytuacja:** Klient zażądał usunięcia wszystkich swoich danych.

```python
from src.rag import ForgetService

forget = ForgetService(...)

# 1. Znajdź wszystkie dokumenty od klienta
docs = engine.search("@clientdomain.com", top_k=100)
print(f"Znaleziono {len(docs)} dokumentów")

# 2. Usuń wszystko od tego nadawcy
result = forget.forget_sender(
    sender="@clientdomain.com",
    reason="RODO - żądanie klienta"
)

print(f"Usunięto {result.total_deleted} elementów")

# 3. Wygeneruj raport
print(f"""
Raport usunięcia danych:
- Data: {result.timestamp}
- Powód: {result.reason}
- Wektory usunięte: {result.vectors_deleted}
- Referencje usunięte: {result.references_deleted}
- ID audytu: {result.audit_id}
""")
```

### 7.6. Scenariusz kreatywny: "Mój dziennik AI"

**Koncepcja:** Digital Twin jako interaktywny dziennik, który rozumie Twoje życie.

```python
# Codzienne podsumowanie
result = engine.query(
    "Podsumuj moje dzisiejsze komunikacje i notatki"
)

# Analiza nastroju (wymaga odpowiednich notatek)
result = engine.query(
    "Jak zmieniał się mój nastrój w tym tygodniu na podstawie moich notatek?"
)

# Wykrywanie wzorców
result = engine.query(
    "Jakie tematy najczęściej pojawiają się w moich notatkach?"
)
```

### 7.7. Scenariusz kreatywny: "Asystent pisania"

**Koncepcja:** Używaj swoich starych tekstów jako bazy stylistycznej.

```python
# Znajdź swój styl pisania
old_emails = engine.search(
    query="",
    top_k=50,
    source_type="email"
)

# Poproś o pomoc w pisaniu (wymaga rozszerzenia P2)
result = engine.query(
    "Na podstawie moich poprzednich maili, jak powinienem odpowiedzieć na tę wiadomość: [treść]?"
)
```

### 7.8. Scenariusz kreatywny: "Second Brain dla freelancera"

**Koncepcja:** Zarządzanie wiedzą o klientach i projektach.

```python
# Struktura katalogów
"""
data/
├── clients/
│   ├── acme/
│   │   ├── briefs/
│   │   ├── feedback/
│   │   └── invoices/
│   └── beta/
│       └── ...
├── projects/
│   ├── website_redesign/
│   └── mobile_app/
└── knowledge/
    ├── tutorials/
    └── references/
"""

# Zapytania kontekstowe
engine.query("Jaki feedback dał mi klient Acme?")
engine.query("Ile zarobiłem w tym kwartale?")
engine.query("Jakie problemy miałem w podobnych projektach?")
```

---

## 8. Integracje i rozszerzenia

### 8.1. Integracja z systemem plików

**Automatyczne wykrywanie zmian:**

```python
from src.storage import DocumentRegistry

registry = DocumentRegistry()

# Wykryj zmienione pliki
changes = registry.get_changed_files("./data/")
print(f"Nowe: {len(changes.get('new', []))}")
print(f"Zmienione: {len(changes.get('modified', []))}")
print(f"Usunięte: {len(changes.get('deleted', []))}")

# Incremental re-index
# (do zaimplementowania w przyszłych wersjach)
```

### 8.2. Integracja z kalendarzem (koncepcja)

```python
# Przyszła funkcjonalność
from ical import Calendar

def sync_calendar(cal_path):
    """Synchronizuj wydarzenia z kalendarzem."""
    with open(cal_path) as f:
        cal = Calendar.from_ical(f.read())

    for event in cal.walk('VEVENT'):
        doc = {
            "source_type": "calendar",
            "content": f"{event['SUMMARY']}: {event['DESCRIPTION']}",
            "date": event['DTSTART'].dt,
            "metadata": {
                "location": event.get('LOCATION'),
                "attendees": [str(a) for a in event.get('ATTENDEE', [])]
            }
        }
        # Index document...
```

### 8.3. Integracja z Obsidian (koncepcja)

```python
# Przyszła funkcjonalność
def sync_obsidian_vault(vault_path):
    """Synchronizuj notatki z Obsidian."""
    for md_file in Path(vault_path).rglob("*.md"):
        # Parsuj frontmatter
        content = md_file.read_text()
        metadata = parse_frontmatter(content)

        # Rozpoznaj typ notatki
        if metadata.get("type") == "decision":
            doc_type = DocumentType.DECISION
        elif metadata.get("type") == "meeting":
            doc_type = DocumentType.NOTE
        else:
            doc_type = DocumentType.NOTE

        # Index with priority...
```

### 8.4. REST API (koncepcja)

```python
# Przyszła funkcjonalność - FastAPI wrapper
from fastapi import FastAPI

app = FastAPI()

@app.post("/query")
async def query(question: str, include_explanation: bool = False):
    engine = get_engine()
    return engine.query(
        question,
        include_explanation=include_explanation
    )

@app.post("/forget")
async def forget(document_id: str, reason: str):
    forget_service = get_forget_service()
    return forget_service.forget_document(document_id, reason)

@app.get("/stats")
async def stats():
    engine = get_engine()
    return engine.get_stats()
```

### 8.5. Webhook'i (koncepcja)

```python
# Przyszła funkcjonalność
def setup_webhooks():
    """Konfiguracja webhooków dla automatyzacji."""

    @on_new_document
    def notify_indexing(doc):
        requests.post(
            "https://your-webhook.com/indexed",
            json={"document_id": doc.id, "type": doc.source_type}
        )

    @on_forget
    def notify_deletion(result):
        requests.post(
            "https://your-webhook.com/deleted",
            json={"count": result.total_deleted}
        )
```

### 8.6. Potencjalne zastosowania

| Zastosowanie | Opis |
|--------------|------|
| **Personal Knowledge Base** | Zorganizuj wszystkie swoje notatki, e-maile i dokumenty |
| **Research Assistant** | Przeszukuj literaturę i notatki badawcze |
| **Legal Discovery** | Przeszukuj dokumenty prawne (offline!) |
| **Customer History** | Pamiętaj wszystkie interakcje z klientami |
| **Medical Records** | Bezpieczny dostęp do dokumentacji medycznej |
| **Journalist Notes** | Organizuj źródła i wywiady |
| **Freelancer CRM** | Zarządzaj wiedzą o klientach i projektach |
| **Family Archive** | Przeszukuj zdjęcia, listy, dokumenty rodzinne |

---

## 9. API Reference

### 9.1. RAGEngine

Główna klasa do interakcji z systemem.

```python
class RAGEngine:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        llm_provider: BaseLLM | None = None,
        chat_history: ChatHistory | None = None,
    ):
        """Inicjalizacja RAG engine.

        Args:
            vector_store: Instancja VectorStore. Jeśli None, tworzy nową.
            llm_provider: Dostawca LLM. Jeśli None, tworzy z ustawień.
            chat_history: Historia czatów. Jeśli None, tworzy nową.
        """

    def query(
        self,
        question: str,
        conversation_id: int | None = None,
        top_k: int | None = None,
        include_sources: bool = True,
        include_explanation: bool = False,
    ) -> dict:
        """Wykonaj zapytanie RAG.

        Args:
            question: Pytanie użytkownika
            conversation_id: ID konwersacji dla kontekstu
            top_k: Liczba dokumentów do pobrania
            include_sources: Czy dołączyć metadane źródeł
            include_explanation: Czy dołączyć wyjaśnienie RAG

        Returns:
            Dict z kluczami: answer, sources, citations, is_grounded,
            no_context_found, conversation_id, query_time_ms,
            [explanation]
        """

    def search(
        self,
        query: str,
        top_k: int | None = None,
        source_type: str | None = None,
    ) -> list[dict]:
        """Wyszukaj dokumenty bez generowania odpowiedzi.

        Args:
            query: Zapytanie wyszukiwania
            top_k: Liczba wyników
            source_type: Filtr po typie źródła

        Returns:
            Lista dokumentów z metadanymi
        """

    def get_stats(self) -> dict:
        """Pobierz statystyki systemu."""

    def set_llm_provider(self, provider: str | BaseLLM) -> None:
        """Zmień dostawcę LLM."""
```

### 9.2. ForgetService

Serwis usuwania danych (RTBF).

```python
class ForgetService:
    def __init__(
        self,
        vector_store: VectorStore,
        chat_history: ChatHistory,
        document_registry: DocumentRegistry,
        audit_logger: AuditLogger | None = None,
    ):
        """Inicjalizacja serwisu usuwania."""

    def forget_document(
        self,
        document_id: str,
        reason: str = "User request",
    ) -> ForgetResult:
        """Usuń pojedynczy dokument ze wszystkich systemów.

        Args:
            document_id: UUID dokumentu
            reason: Powód usunięcia (do audytu)

        Returns:
            ForgetResult z podsumowaniem operacji
        """

    def forget_sender(
        self,
        sender: str,
        reason: str = "GDPR request",
    ) -> ForgetResult:
        """Usuń wszystkie dokumenty od nadawcy."""

    def forget_by_source_type(
        self,
        source_type: str,
        reason: str = "Bulk deletion",
    ) -> ForgetResult:
        """Usuń wszystkie dokumenty danego typu."""
```

### 9.3. VectorStore

Interfejs do bazy wektorowej Qdrant.

```python
class VectorStore:
    def __init__(
        self,
        collection_name: str | None = None,
        embedding_model: str | None = None,
    ):
        """Inicjalizacja store'a wektorowego."""

    def add_documents(self, documents: list) -> int:
        """Dodaj dokumenty do indeksu."""

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict]:
        """Wyszukaj dokumenty przez podobieństwo."""

    def search_with_priority(
        self,
        query: str,
        top_k: int = 10,
        fetch_k: int = 50,
        filters: dict | None = None,
    ) -> list[dict]:
        """Wyszukaj z ważeniem priorytetów."""

    def delete_document(self, document_id: str) -> bool:
        """Usuń dokument po ID."""

    def delete_by_filter(self, filters: dict) -> int:
        """Usuń dokumenty pasujące do filtru."""

    def get_stats(self) -> dict:
        """Pobierz statystyki kolekcji."""
```

### 9.4. Typy danych

```python
@dataclass
class Citation:
    document_id: str
    source_type: str
    filename: str
    date: str
    fragment: str
    score: float

@dataclass
class ForgetResult:
    success: bool
    vectors_deleted: int
    references_deleted: int
    documents_deleted: int
    total_deleted: int
    timestamp: datetime
    reason: str
    audit_id: int | None

@dataclass
class DocumentPriority:
    type_score: float
    recency_score: float
    approval_score: float
    priority_score: float

class DocumentType(IntEnum):
    DECISION = 100
    NOTE = 70
    EMAIL = 50
    CONVERSATION = 30

class ApprovalStatus(IntEnum):
    PINNED = 50
    APPROVED = 30
    AUTOMATIC = 0
```

---

## 10. FAQ i rozwiązywanie problemów

### 10.1. Najczęstsze pytania

**P: Czy moje dane są bezpieczne?**

O: Tak. W trybie offline (OFFLINE_MODE=true) wszystkie dane pozostają na Twoim komputerze. Nawet gdy używasz OpenAI/Anthropic, tylko fragmenty kontekstowe są wysyłane (nigdy cały indeks).

**P: Jaki model LLM jest najlepszy?**

O: Zależy od potrzeb:
- **Prywatność**: GPT4All (lokalnie, wolniej)
- **Jakość**: GPT-4-turbo lub Claude 3 (wymaga internetu)
- **Koszt**: GPT4All (darmowe) lub GPT-3.5-turbo (tanie)

**P: Ile miejsca zajmuje indeks?**

O: ~1 MB na 1000 dokumentów (fragmenty 512 tokenów). Model GPT4All: ~4 GB.

**P: Czy mogę indeksować PDF?**

O: Nie w wersji P0. Planowane w P2.

**P: Jak często powinienem re-indeksować?**

O: System automatycznie wykrywa zmiany. Uruchom `ingest.py` po dodaniu nowych plików.

### 10.2. Rozwiązywanie problemów

#### Qdrant nie startuje

```bash
# Sprawdź logi
docker logs qdrant

# Restart
docker-compose down
docker-compose up -d

# Sprawdź port
curl http://localhost:6333/health
```

#### Błąd "Connection refused"

```bash
# Sprawdź czy Qdrant działa
docker ps | grep qdrant

# Sprawdź konfigurację
cat .env | grep QDRANT
```

#### Wolne odpowiedzi z GPT4All

Przyczyna: Model działa na CPU.

Rozwiązania:
1. Użyj mniejszego modelu
2. Zmniejsz TOP_K (mniej kontekstu)
3. Rozważ GPU (wymaga kompilacji llama-cpp-python z CUDA)

#### "No documents found"

```bash
# Sprawdź czy dane są zindeksowane
python scripts/ingest.py --stats

# Re-indeksuj
python scripts/ingest.py --source ./data/ --reset
```

#### Błąd "OfflineModeError"

```python
# Sprawdź konfigurację
from src.config import settings
print(f"Offline: {settings.offline_mode}")
print(f"Allow cloud: {settings.allow_cloud_llm}")
print(f"Available: {settings.available_llm_providers}")

# Zmień w .env lub:
# OFFLINE_MODE=false
# LLM_PROVIDER=gpt4all
```

#### Cytaty nie pojawiają się

1. Sprawdź czy `include_sources=True`
2. Sprawdź czy dokumenty mają metadane (date, source_type)
3. Sprawdź scoring — może dokumenty mają niski priorytet

### 10.3. Logowanie debugowania

```python
import logging

# Włącz szczegółowe logi
logging.basicConfig(level=logging.DEBUG)

# Lub tylko dla konkretnych modułów
logging.getLogger("src.rag").setLevel(logging.DEBUG)
logging.getLogger("src.indexer").setLevel(logging.DEBUG)
```

### 10.4. Testowanie

```bash
# Uruchom testy (jeśli dostępne)
pytest tests/

# Test pojedynczego modułu
pytest tests/test_citations.py -v

# Test z coverage
pytest --cov=src tests/
```

---

## Załączniki

### A. Słownik pojęć

| Termin | Definicja |
|--------|-----------|
| **RAG** | Retrieval-Augmented Generation — technika łącząca wyszukiwanie z generowaniem |
| **Embedding** | Reprezentacja wektorowa tekstu umożliwiająca wyszukiwanie semantyczne |
| **Grounding** | Zakotwiczenie odpowiedzi w źródłach (przeciwieństwo halucynacji) |
| **RTBF** | Right To Be Forgotten — prawo do usunięcia danych (RODO) |
| **Chunking** | Podział dokumentu na mniejsze fragmenty do indeksowania |
| **Top-K** | Liczba najbardziej podobnych dokumentów do pobrania |

### B. Struktura plików projektu

```
digital-twin/
├── src/
│   ├── config.py           # Konfiguracja
│   ├── loaders/            # Parsery plików
│   │   ├── base.py
│   │   ├── text_loader.py
│   │   ├── email_loader.py
│   │   ├── whatsapp_loader.py
│   │   └── messenger_loader.py
│   ├── indexer/            # Baza wektorowa
│   │   └── vector_store.py
│   ├── llm/                # Dostawcy LLM
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── gpt4all_provider.py
│   │   ├── openai_provider.py
│   │   └── anthropic_provider.py
│   ├── rag/                # Silnik RAG
│   │   ├── query_engine.py
│   │   ├── citations.py
│   │   ├── priority.py
│   │   ├── explainability.py
│   │   └── forget.py
│   ├── storage/            # Persystencja
│   │   ├── chat_history.py
│   │   ├── document_registry.py
│   │   └── audit.py
│   └── ui/                 # Interfejs
│       └── app.py
├── scripts/
│   └── ingest.py           # Skrypt importu
├── data/                   # Dane do zindeksowania
├── storage/                # Bazy SQLite
├── doc/                    # Dokumentacja
├── .env                    # Konfiguracja środowiska
└── docker-compose.yml      # Qdrant
```

### C. Changelog

**Wersja 1.0 (P0 Critical)**
- Grounded Answers z cytatami
- Offline Mode
- Priority Rules
- Explainability
- Forget/RTBF

---

**Dokumentacja wygenerowana dla Digital Twin v1.0**

*Pytania? Zgłoś issue na GitHub.*
