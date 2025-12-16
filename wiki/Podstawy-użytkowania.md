# Podstawy użytkowania

Naucz się efektywnie korzystać z Digital Twin — od importu danych po zadawanie pytań.

---

## Spis treści

1. [Import danych](#import-danych)
2. [Interfejs użytkownika (Streamlit)](#interfejs-użytkownika-streamlit)
3. [Zadawanie pytań](#zadawanie-pytań)
4. [Zarządzanie konwersacjami](#zarządzanie-konwersacjami)
5. [Wyszukiwanie dokumentów](#wyszukiwanie-dokumentów)
6. [Użycie programistyczne (Python)](#użycie-programistyczne-python)

---

## Import danych

### Obsługiwane formaty

| Typ danych | Formaty | Katalog docelowy |
|------------|---------|------------------|
| **Notatki** | `.txt`, `.md` | `data/notes/` |
| **E-maile** | `.eml`, `.mbox` | `data/emails/` |
| **WhatsApp** | `.txt` (eksport z aplikacji) | `data/whatsapp/` |
| **Messenger** | `.json` (eksport z Facebooka) | `data/messenger/` |

### Przygotowanie danych

#### Notatki tekstowe

```bash
# Skopiuj swoje notatki
cp ~/Documents/notes/*.md data/notes/
cp ~/Documents/notes/*.txt data/notes/

# Struktura przykładowa:
data/notes/
├── 2024-01-15-spotkanie-z-klientem.md
├── pomysły-na-projekt.txt
└── lista-zadań.md
```

#### E-maile (.eml)

```bash
# Eksport z Thunderbird/Outlook
cp ~/Mail/Archives/*.eml data/emails/

# Lub z pliku MBOX (Gmail Takeout)
cp ~/Downloads/All\ mail.mbox data/emails/
```

#### WhatsApp

1. Otwórz WhatsApp na telefonie
2. Wejdź do rozmowy → Menu (⋮) → Więcej → Eksportuj czat
3. Wybierz "Bez multimediów"
4. Prześlij plik `.txt` do `data/whatsapp/`

```bash
# Przykładowa struktura:
data/whatsapp/
├── Czat WhatsApp z Anna.txt
├── Czat WhatsApp z Praca Team.txt
└── Czat WhatsApp z Rodzina.txt
```

#### Messenger (Facebook)

1. Wejdź na facebook.com/dyi
2. Pobierz informacje → Wiadomości → Format JSON
3. Rozpakuj archiwum
4. Skopiuj pliki `.json`

```bash
cp ~/Downloads/facebook-*/messages/inbox/*/message_*.json data/messenger/
```

### Uruchomienie importu

```bash
# Import wszystkich typów danych
python scripts/ingest.py --source ./data/

# Import tylko określonych typów
python scripts/ingest.py --source ./data/ --types text email
python scripts/ingest.py --source ./data/ --types whatsapp messenger

# Import z resetem (usuwa stary indeks)
python scripts/ingest.py --source ./data/ --reset

# Tylko statystyki (bez importu)
python scripts/ingest.py --stats
```

### Przykładowy output

```
Connecting to Qdrant...
Loading data from: ./data

  Loading text files...
    Found 42 documents
  Loading email files...
    Found 156 documents
  Loading whatsapp files...
    Found 23 documents
  Loading messenger files...
    Found 89 documents

Indexing 310 documents...
Successfully indexed 310 documents.

Index now contains 2847 vectors.
```

### Import przyrostowy

System automatycznie wykrywa nowe i zmienione pliki:

```bash
# Dodaj nowe pliki
cp ~/new_notes/*.md data/notes/

# Uruchom import (doda tylko nowe)
python scripts/ingest.py --source ./data/
```

---

## Interfejs użytkownika (Streamlit)

### Uruchomienie

```bash
streamlit run src/ui/app.py

# Z niestandardowym portem:
streamlit run src/ui/app.py --server.port 8080
```

Otwórz w przeglądarce: **http://localhost:8501**

### Elementy interfejsu

```
┌──────────────────────────────────────────────────────────────┐
│  🤖 Digital Twin                                    [≡]     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌────────────────────────────────────────┐ │
│  │  SIDEBAR    │  │           GŁÓWNY PANEL                 │ │
│  │             │  │                                        │ │
│  │  LLM:       │  │  [Historia konwersacji]                │ │
│  │  ○ gpt4all  │  │                                        │ │
│  │  ○ openai   │  │  User: Pytanie...                      │ │
│  │  ○ anthropic│  │                                        │ │
│  │             │  │  Assistant: Odpowiedź...               │ │
│  │  ──────────│  │    📎 Źródła: [email] [note]           │ │
│  │             │  │                                        │ │
│  │  Konwersacje│  │                                        │ │
│  │  • Projekt X│  │                                        │ │
│  │  • Sprawy   │  │                                        │ │
│  │  + Nowa     │  │  ┌──────────────────────────────────┐  │ │
│  │             │  │  │  Wpisz pytanie...            [➤] │  │ │
│  │  ──────────│  │  └──────────────────────────────────┘  │ │
│  │  Indeks:    │  │                                        │ │
│  │  2847 docs  │  └────────────────────────────────────────┘ │
│  └─────────────┘                                             │
└──────────────────────────────────────────────────────────────┘
```

### Sidebar

- **LLM Provider** — wybierz dostawcę modelu językowego
- **Konwersacje** — lista zapisanych rozmów
- **Nowa konwersacja** — rozpocznij czystą sesję
- **Status indeksu** — liczba zindeksowanych dokumentów

### Wskaźniki trybu

| Wskaźnik | Znaczenie |
|----------|-----------|
| 🟢 `ONLINE` | Dostępne wszystkie LLM |
| 🟡 `LOCAL ONLY` | Tylko GPT4All (ALLOW_CLOUD_LLM=false) |
| 🔴 `OFFLINE` | Tryb offline aktywny |

---

## Zadawanie pytań

### Podstawowe pytania

```
Pytanie: O czym pisałem w ostatnim mailu do Marka?

Odpowiedź: W ostatnim mailu do Marka (z 15 grudnia 2024) pisałeś o:
1. Terminie oddania projektu (do końca miesiąca)
2. Budżecie na dodatkowe funkcje (5000 PLN)
3. Spotkaniu w przyszłym tygodniu

[Źródło: email, 2024-12-15, "Cześć Marek, chciałem potwierdzić..."]
```

### Pytania z kontekstem

```
Pytanie: Jakie decyzje podjąłem w sprawie projektu X?

Odpowiedź: Na podstawie Twoich dokumentów, w sprawie projektu X podjąłeś następujące decyzje:

1. **Technologia**: React + Node.js (notatka z 2024-11-01)
   [Źródło: note, 2024-11-01, "Decyzja: wybieramy React..."]

2. **Budżet**: 50,000 PLN (email z 2024-11-15)
   [Źródło: email, 2024-11-15, "Budżet został zatwierdzony..."]

3. **Deadline**: 31 marca 2025 (WhatsApp z 2024-11-20)
   [Źródło: whatsapp, 2024-11-20, "Ok, deadline 31.03..."]
```

### Pytania porównawcze

```
Pytanie: Jak zmieniło się moje podejście do zdalnej pracy w tym roku?

Odpowiedź: Analiza Twoich dokumentów pokazuje ewolucję:

📅 **Styczeń 2024**: Sceptycyzm
"Wolę pracować z biura, łatwiej się skupić"
[Źródło: note, 2024-01-15, ...]

📅 **Czerwiec 2024**: Adaptacja
"Wypracowałem rutynę, jest ok"
[Źródło: email, 2024-06-20, ...]

📅 **Grudzień 2024**: Akceptacja
"Zdalnie pracuję efektywniej"
[Źródło: note, 2024-12-01, ...]
```

### Dobre praktyki zadawania pytań

| ✅ Dobre pytanie | ❌ Złe pytanie |
|------------------|----------------|
| "Co ustaliliśmy z Anną w sprawie projektu?" | "Co z Anną?" |
| "Jakie były moje argumenty za wyborem React?" | "React" |
| "Kiedy ostatnio kontaktowałem się z klientem X?" | "Klient X" |
| "Podsumuj moje notatki z konferencji DevConf" | "Konferencja" |

### Odpowiedzi "Nie znaleziono"

Gdy system nie znajdzie odpowiedzi:

```
Pytanie: Jaki jest mój numer konta bankowego?

Odpowiedź: Nie mogłem znaleźć informacji o numerze konta bankowego
w Twoich zindeksowanych dokumentach.

Sprawdź czy:
- Dokumenty zawierające te dane zostały zindeksowane
- Użyto odpowiednich słów kluczowych
```

---

## Zarządzanie konwersacjami

### Tworzenie konwersacji

W UI:
1. Kliknij "+ Nowa konwersacja" w sidebarze
2. Podaj nazwę (np. "Projekt X", "Sprawy osobiste")

W Python:
```python
from src.storage import ChatHistory

history = ChatHistory()
conv_id = history.create_conversation("Projekt X")
print(f"Utworzono konwersację: {conv_id}")
```

### Kontynuowanie konwersacji

System zachowuje kontekst poprzednich pytań:

```
# Pierwsze pytanie:
User: Kto jest PM w projekcie X?
Assistant: PM projektu X jest Anna Kowalska.

# Drugie pytanie (kontekst zachowany):
User: Kiedy z nią ostatnio rozmawiałem?
Assistant: Ostatnia rozmowa z Anną Kowalską miała miejsce
12 grudnia 2024 przez WhatsApp.
```

### Przeglądanie historii

```python
from src.storage import ChatHistory

history = ChatHistory()

# Lista konwersacji
conversations = history.get_conversations()
for conv in conversations:
    print(f"{conv.id}: {conv.title} ({conv.created_at})")

# Wiadomości w konwersacji
messages = history.get_messages(conv_id)
for msg in messages:
    print(f"[{msg.role}] {msg.content[:50]}...")
```

### Usuwanie konwersacji

```python
history.delete_conversation(conv_id)
```

---

## Wyszukiwanie dokumentów

### Wyszukiwanie bez generowania odpowiedzi

```python
from src.rag import RAGEngine

engine = RAGEngine()

# Podstawowe wyszukiwanie
results = engine.search("umowa najmu", top_k=10)

for doc in results:
    print(f"📄 {doc['filename']}")
    print(f"   Typ: {doc['source_type']}")
    print(f"   Score: {doc['score']:.2f}")
    print(f"   Fragment: {doc['content'][:100]}...")
    print()
```

### Filtrowanie po typie źródła

```python
# Tylko e-maile
results = engine.search("spotkanie", source_type="email")

# Tylko notatki
results = engine.search("decyzja", source_type="note")

# Tylko WhatsApp
results = engine.search("piątek", source_type="whatsapp")
```

### Wyszukiwanie z priorytetami

```python
from src.indexer import VectorStore

vs = VectorStore()

# Pobierz więcej kandydatów, przefiltruj z priorytetami
results = vs.search_with_priority(
    query="projekt X",
    top_k=5,      # Zwróć 5 najlepszych
    fetch_k=50,   # Pobierz 50 kandydatów do rankingu
)

for doc in results:
    print(f"{doc['filename']}: sim={doc['similarity']:.2f}, pri={doc['priority']:.2f}")
```

---

## Użycie programistyczne (Python)

### Podstawowe zapytanie

```python
from src.rag import RAGEngine

engine = RAGEngine()

result = engine.query("Jakie mam zadania na ten tydzień?")

print("Odpowiedź:", result["answer"])
print("Liczba źródeł:", len(result["sources"]))
print("Uziemione:", result["is_grounded"])
```

### Zapytanie z wyjaśnieniem

```python
result = engine.query(
    question="Podsumuj moje spotkania w tym miesiącu",
    include_explanation=True
)

# Wyświetl wyjaśnienie
exp = result["explanation"]
print(f"Czas zapytania: {exp['timing']['total_ms']:.0f}ms")
print(f"Dokumentów użyto: {len(exp['documents_retrieved'])}")

for doc in exp["documents_retrieved"]:
    print(f"  - {doc['filename']}: {doc['final_score']:.2f}")
```

### Zapytanie w kontekście konwersacji

```python
from src.storage import ChatHistory
from src.rag import RAGEngine

history = ChatHistory()
engine = RAGEngine()

# Utwórz lub użyj istniejącej konwersacji
conv_id = history.create_conversation("Analiza projektów")

# Pierwsze pytanie
result1 = engine.query(
    "Jakie projekty prowadzę?",
    conversation_id=conv_id
)

# Drugie pytanie (z kontekstem)
result2 = engine.query(
    "Który z nich ma najbliższy deadline?",
    conversation_id=conv_id
)
```

### Zmiana dostawcy LLM

```python
from src.rag import RAGEngine

engine = RAGEngine()

# Sprawdź aktualny
print(f"Aktualny LLM: {engine.llm_provider.name}")

# Zmień na OpenAI (jeśli dostępny)
engine.set_llm_provider("openai")

# Lub na Anthropic
engine.set_llm_provider("anthropic")

# Powrót do lokalnego
engine.set_llm_provider("gpt4all")
```

### Statystyki systemu

```python
stats = engine.get_stats()

print("📊 Statystyki:")
print(f"  Indeks istnieje: {stats['index']['exists']}")
print(f"  Dokumentów: {stats['index']['points_count']}")
print(f"  LLM: {stats['llm_provider']['name']}")
print(f"  Lokalny: {stats['llm_provider']['is_local']}")
```

### Kompletny przykład skryptu

```python
#!/usr/bin/env python3
"""Przykład użycia Digital Twin z kodu."""

from src.rag import RAGEngine
from src.storage import ChatHistory

def main():
    # Inicjalizacja
    engine = RAGEngine()
    history = ChatHistory()

    # Sprawdź status
    stats = engine.get_stats()
    print(f"📚 Indeks zawiera {stats['index']['points_count']} dokumentów")
    print(f"🤖 LLM: {stats['llm_provider']['name']}")

    # Utwórz konwersację
    conv_id = history.create_conversation("Sesja CLI")

    # Interaktywna pętla
    print("\n💬 Digital Twin CLI (wpisz 'exit' aby wyjść)\n")

    while True:
        question = input("Ty: ").strip()

        if question.lower() == 'exit':
            break

        if not question:
            continue

        result = engine.query(
            question,
            conversation_id=conv_id,
            include_explanation=True
        )

        print(f"\n🤖 Assistant: {result['answer']}")

        if result['sources']:
            print(f"\n📎 Źródła ({len(result['sources'])}):")
            for src in result['sources'][:3]:
                print(f"   - {src['source_type']}: {src['filename']}")

        print()

if __name__ == "__main__":
    main()
```

Zapisz jako `cli.py` i uruchom:

```bash
python cli.py
```

---

<p align="center">
  <a href="Konfiguracja">← Konfiguracja</a> |
  <a href="Home">Strona główna</a> |
  <a href="FR-P0-1-Grounded-Answers">FR-P0-1: Grounded Answers →</a>
</p>
