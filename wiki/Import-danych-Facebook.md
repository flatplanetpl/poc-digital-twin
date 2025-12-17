# Import danych Facebook

Kompletna instrukcja eksportu i importu danych Facebook/Messenger do Digital Twin.

---

## Spis treści

1. [Eksport danych z Facebook](#eksport-danych-z-facebook)
2. [Struktura eksportu](#struktura-eksportu)
3. [Import do Digital Twin](#import-do-digital-twin)
4. [Dostępne loadery](#dostępne-loadery)
5. [Contact Graph](#contact-graph)
6. [Pytania o osoby](#pytania-o-osoby)
7. [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Eksport danych z Facebook

### Krok 1: Żądanie eksportu

1. Zaloguj się na [facebook.com](https://facebook.com)
2. Przejdź do: **Ustawienia i prywatność** → **Ustawienia** → **Twoje informacje na Facebooku**
3. Kliknij **Pobierz swoje informacje**
4. Lub bezpośrednio: [facebook.com/dyi](https://www.facebook.com/dyi)

### Krok 2: Konfiguracja eksportu

**Zalecane ustawienia:**

| Opcja | Wartość | Uwagi |
|-------|---------|-------|
| **Format** | JSON | Wymagane dla Digital Twin |
| **Jakość mediów** | Niska | Oszczędza miejsce |
| **Zakres dat** | Wszystkie | Lub wybrany okres |

**Kategorie do zaznaczenia:**

- [x] Wiadomości (Messages)
- [x] Informacje osobiste (Personal Information)
- [x] Połączenia (Connections) - znajomi
- [x] Zalogowane informacje (Logged Information)
- [ ] Zdjęcia i filmy - opcjonalnie (duże!)
- [ ] Posty - opcjonalnie

### Krok 3: Pobranie i rozpakowanie

1. Facebook przygotuje eksport (może trwać 1-24h)
2. Pobierzesz plik `.zip` (zwykle 100MB - 5GB)
3. Rozpakuj do katalogu `data/messenger/`:

```bash
# Rozpakuj eksport
unzip facebook-export.zip -d data/messenger/

# Struktura po rozpakowaniu:
data/messenger/
├── messages/
├── personal_information/
├── connections/
├── logged_information/
└── your_facebook_activity/
```

---

## Struktura eksportu

### Drzewo katalogów

```
facebook-export/
├── messages/                          # SZYFROWANE E2E (jeśli włączone)
│   └── inbox/                         # Mogą być puste
│
├── your_facebook_activity/            # GŁÓWNE ŹRÓDŁO WIADOMOŚCI
│   └── messages/
│       └── inbox/
│           ├── johnsmith_abc123/
│           │   ├── message_1.json     # Konwersacja
│           │   ├── message_2.json     # Kontynuacja (>10k wiadomości)
│           │   └── photos/            # Zdjęcia z konwersacji
│           └── groupchat_xyz456/
│               └── message_1.json
│
├── personal_information/
│   └── profile_information/
│       └── profile_information.json   # Twój profil
│
├── connections/
│   └── friends/
│       └── your_friends.json          # Lista znajomych (~1000+)
│
└── logged_information/
    ├── location/
    │   ├── device_location.json       # Historia lokalizacji GPS
    │   └── primary_location.json      # Główna lokalizacja
    ├── search/
    │   └── your_search_history.json   # Historia wyszukiwania
    └── other_logged_information/
        ├── ads_interests.json         # Zainteresowania reklamowe
        └── locations_of_interest.json # Odwiedzane miejsca
```

### Format wiadomości (message_N.json)

```json
{
  "participants": [
    {"name": "Jan Kowalski"},
    {"name": "Damian Jarosch"}
  ],
  "messages": [
    {
      "sender_name": "Jan Kowalski",
      "timestamp_ms": 1702834567890,
      "content": "Cześć, co słychać?",
      "reactions": [{"reaction": "👍", "actor": "Damian Jarosch"}],
      "photos": [{"uri": "photos/123.jpg"}],
      "share": {"link": "https://example.com"}
    }
  ],
  "title": "Jan Kowalski",
  "is_still_participant": true,
  "thread_type": "Regular",
  "thread_path": "inbox/jankowalski_abc123"
}
```

> **Uwaga o kodowaniu:** Facebook eksportuje tekst z błędnym kodowaniem (mojibake).
> Digital Twin automatycznie konwertuje `Cze\u015b\u0107` → `Cześć`.

---

## Import do Digital Twin

### Szybki start

```bash
# Import wszystkich danych Facebook jedną komendą
python scripts/ingest.py --source ./data/messenger --types facebook

# Lub wybrane typy:
python scripts/ingest.py --source ./data/messenger --types messenger,profile,contacts
```

### Szczegółowy import

```bash
# Tylko wiadomości Messenger
python scripts/ingest.py --source ./data/messenger --types messenger

# Tylko profil użytkownika
python scripts/ingest.py --source ./data/messenger --types profile

# Tylko lista znajomych
python scripts/ingest.py --source ./data/messenger --types contacts

# Tylko lokalizacje
python scripts/ingest.py --source ./data/messenger --types location

# Tylko historia wyszukiwania
python scripts/ingest.py --source ./data/messenger --types search

# Tylko zainteresowania reklamowe
python scripts/ingest.py --source ./data/messenger --types interests
```

### Przykładowy output

```
Connecting to Qdrant...
Contact registry initialized.

Loading data from: ./data/messenger
  Loading messenger files...
    Processing inbox/jankowalski_abc123...
    Processing inbox/mariakowalska_def456...
    ... (734 konwersacji)
    Found 12847 documents (734 conversations)
  Loading profile files...
    Found 1 document
  Loading contacts files...
    Found 1084 documents (friends + phone contacts)
  Loading location files...
    Found 156 documents
  Loading search files...
    Found 234 documents
  Loading interests files...
    Found 1 document (47 interests)

Indexing 14323 documents...
Successfully indexed 14323 documents.
Index now contains 42891 vectors.

Contact Registry:
  Total contacts: 1247
  Total messages tracked: 54321
  By source: {'messenger': 1084, 'whatsapp': 163}
```

---

## Dostępne loadery

### MessengerLoader

**Plik:** `src/loaders/messenger_loader.py`

Parsuje wiadomości z Messenger/Facebook Chat.

**Cechy:**
- Wykrywanie typu konwersacji (individual/group/broadcast)
- Ekstrakcja mediów (zdjęcia, filmy, linki)
- Zliczanie reakcji
- Integracja z ContactRegistry
- Automatyczna konwersja kodowania (mojibake fix)

**Metadata:**

| Pole | Opis |
|------|------|
| `sender` | Nazwa nadawcy |
| `participants` | Lista uczestników |
| `thread_title` | Tytuł konwersacji |
| `thread_type` | `individual` / `group` / `broadcast` |
| `date` | Data wiadomości |
| `has_media` | Czy zawiera media |
| `media_types` | Lista typów mediów |
| `reaction_count` | Liczba reakcji |
| `source_type` | `messenger` |

### ProfileLoader

**Plik:** `src/loaders/profile_loader.py`

Parsuje profil użytkownika Facebook.

**Źródło:** `personal_information/profile_information/profile_information.json`

**Metadata:**

| Pole | Opis |
|------|------|
| `profile_type` | `self` |
| `full_name` | Imię i nazwisko |
| `email` | Adresy email |
| `phone` | Numery telefonu |
| `birthday` | Data urodzenia |
| `city` | Obecne miasto |
| `hometown` | Miasto rodzinne |
| `work_history` | Historia zatrudnienia (JSON) |
| `education` | Wykształcenie (JSON) |
| `family_members` | Relacje rodzinne (JSON) |

**Priorytet:** `PROFILE = 120` (najwyższy dla self-context)

### ContactsLoader

**Plik:** `src/loaders/contacts_loader.py`

Parsuje listę znajomych i kontakty z telefonu.

**Źródła:**
- `connections/friends/your_friends.json`
- `personal_information/other_personal_information/contacts_uploaded_from_your_phone.json`

**Metadata:**

| Pole | Opis |
|------|------|
| `contact_name` | Imię kontaktu |
| `contact_type` | `friend` / `phone_contact` |
| `friendship_date` | Data zawarcia znajomości |
| `normalized_name` | Znormalizowane imię (lowercase) |
| `phone_numbers` | Lista numerów (dla phone_contact) |
| `emails` | Lista emaili (dla phone_contact) |

### LocationLoader

**Plik:** `src/loaders/location_loader.py`

Parsuje historię lokalizacji.

**Źródła:**
- `logged_information/location/device_location.json`
- `logged_information/location/primary_location.json`
- `logged_information/other_logged_information/locations_of_interest.json`

**Metadata:**

| Pole | Opis |
|------|------|
| `location_type` | `device` / `primary` / `interest` |
| `latitude`, `longitude` | Koordynaty GPS |
| `city`, `region`, `country` | Lokalizacja tekstowa |
| `date` | Data |

### SearchHistoryLoader

**Plik:** `src/loaders/search_history_loader.py`

Parsuje historię wyszukiwania Facebook.

**Źródło:** `logged_information/search/your_search_history.json`

**Opcje:**
- `group_by`: `day` (domyślnie) lub `week`

**Metadata:**

| Pole | Opis |
|------|------|
| `search_count` | Liczba wyszukiwań w grupie |
| `date_range` | Zakres dat grupy |
| `searches` | Lista wyszukiwanych fraz |

### AdsInterestsLoader

**Plik:** `src/loaders/ads_interests_loader.py`

Parsuje zainteresowania reklamowe Facebook.

**Źródło:** `logged_information/other_logged_information/ads_interests.json`

**Automatyczna kategoryzacja:**
- Technology, Business, Entertainment, Sports, Lifestyle, Travel, Food, Health, Science, Other

**Metadata:**

| Pole | Opis |
|------|------|
| `interests_count` | Liczba zainteresowań |
| `categories` | Wykryte kategorie |
| `interests_by_category` | Zainteresowania per kategoria (JSON) |

---

## Contact Graph

### Czym jest Contact Graph?

Contact Graph analizuje relacje między Tobą a kontaktami na podstawie:
- Liczby wiadomości
- Częstotliwości interakcji
- Różnorodności kanałów (Messenger + WhatsApp + Email)
- Recency (świeżość kontaktu)

### Interaction Score

```
score = 0.4 * frequency + 0.4 * recency + 0.2 * diversity

Gdzie:
- frequency = min(messages_per_month / 100, 0.4)
- recency = max(1 - days_since_last / 365, 0)
- diversity = 0.2 jeśli kontakt z wielu źródeł
```

### Przykłady użycia

```python
from src.graph import ContactGraph
from src.storage.contact_registry import ContactRegistry

# Inicjalizacja
registry = ContactRegistry()
graph = ContactGraph(registry, vector_store)

# Kto jest moim najczęstszym rozmówcą?
top_contacts = graph.get_top_contacts(limit=10)
for contact in top_contacts:
    print(f"{contact.contact_name}: {contact.interaction_score:.2f}")
# Ewa Kowalska: 0.87
# Jan Nowak: 0.72
# ...

# Z kim rozmawiam o pracy?
work_contacts = graph.find_contacts_by_topic("praca projekt deadline")
# [("Jan Nowak", 0.92), ("Maria Wiśniewska", 0.78)]

# Szczegóły relacji
rel = graph.get_relationship("Ewa Kowalska")
print(f"Wiadomości: {rel.message_count}")
print(f"Pierwszy kontakt: {rel.first_interaction}")
print(f"Ostatni kontakt: {rel.last_interaction}")
print(f"Źródła: {rel.sources}")  # ['messenger', 'whatsapp']
```

---

## Pytania o osoby

Digital Twin automatycznie rozpoznaje pytania o konkretne osoby.

### Przykłady zapytań

```
"Co Ewa mówiła o wakacjach?"
→ Filtruje po: sender="Ewa"
→ Szuka: "wakacje"

"Maile od Jana w grudniu 2023"
→ Filtruje po: sender="Jan", source_type="email", date=2023-12
→ Szuka: wszystko

"Kiedy ostatnio rozmawiałem z Marią?"
→ Filtruje po: sender="Maria"
→ Sortuje po: date DESC

"Wiadomości z WhatsApp o projekcie Alpha"
→ Filtruje po: source_type="whatsapp"
→ Szuka: "projekt Alpha"
```

### Jak to działa?

1. **QueryPreprocessor** analizuje pytanie
2. Wyciąga **person_filter**, **date_range**, **source_filter**
3. Przekazuje filtry do **Qdrant MetadataFilters**
4. Wyszukuje wektory z pasującymi metadanymi

```python
# src/rag/query_preprocessor.py

preprocessor = QueryPreprocessor()
result = preprocessor.preprocess("Co Ewa mówiła o wakacjach?")

# result:
# PreprocessedQuery(
#     clean_query="Co mówiła o wakacjach?",
#     person_filter="Ewa",
#     date_range=None,
#     source_filter=None,
#     extracted_filters={"person": "Ewa"}
# )
```

---

## Rozwiązywanie problemów

### Problem: "Brak wiadomości w eksporcie"

Wiadomości mogą być w dwóch lokalizacjach:
1. `messages/inbox/` - wiadomości szyfrowane E2E
2. `your_facebook_activity/messages/inbox/` - standardowe wiadomości

Digital Twin szuka w obu lokalizacjach.

```bash
# Sprawdź gdzie są wiadomości
find data/messenger -name "message_*.json" | head -5
```

### Problem: "Dziwne znaki w wiadomościach"

Facebook eksportuje z błędnym kodowaniem (mojibake):
- `Cze\u015b\u0107` zamiast `Cześć`
- `\u00c5\u00bc` zamiast `ż`

**Rozwiązanie:** Digital Twin automatycznie konwertuje kodowanie.

```python
# Wewnętrzna konwersja (automatyczna)
def fix_encoding(text: str) -> str:
    try:
        return text.encode("latin-1").decode("utf-8")
    except:
        return text
```

### Problem: "Za dużo dokumentów"

Jeśli masz tysiące konwersacji:

```bash
# Importuj tylko ostatni rok
# (wymagana ręczna filtracja - przenieś starsze pliki)

# Lub importuj tylko najważniejsze typy
python scripts/ingest.py --types messenger,profile,contacts
```

### Problem: "Wolny import"

```bash
# Sprawdź liczbę plików
find data/messenger -name "*.json" | wc -l

# Dla dużych eksportów (>1000 plików) import może trwać kilka minut
# Progres widoczny w konsoli
```

### Problem: "Brak znajomych w eksporcie"

Upewnij się że zaznaczyłeś **Connections** przy eksporcie.

Plik powinien być w: `connections/friends/your_friends.json`

---

## Priorytety dokumentów

| Typ | Priorytet | Opis |
|-----|:---------:|------|
| Profile | 120 | Twój profil (najwyższy dla self-context) |
| Decision | 100 | Jawne decyzje |
| Note | 70 | Notatki osobiste |
| Email | 50 | Korespondencja email |
| Contact | 40 | Informacje o kontaktach |
| Conversation | 30 | Wiadomości Messenger/WhatsApp |
| Interests | 25 | Zainteresowania reklamowe |
| Location | 20 | Historia lokalizacji |
| Search History | 10 | Historia wyszukiwania (najniższy) |

---

## Powiązane

- **[Instalacja](Instalacja)** — pełna instrukcja instalacji
- **[Pipelines](Pipelines)** — szczegóły przetwarzania danych
- **[FR-P0-3: Priority Rules](FR-P0-3-Priority-Rules)** — system priorytetów
- **[FR-P0-5: Forget/RTBF](FR-P0-5-Forget-RTBF)** — usuwanie danych

---

<p align="center">
  <a href="Pipelines">← Pipelines</a> |
  <a href="Home">Strona główna</a> |
  <a href="Scenariusze-użycia">Scenariusze użycia →</a>
</p>
