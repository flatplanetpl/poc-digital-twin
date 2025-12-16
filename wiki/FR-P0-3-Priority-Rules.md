# FR-P0-3: Priority Rules

**Status:** ✅ Zaimplementowane (v1.0)

System inteligentnego ważenia dokumentów — **decyzje > notatki > czaty**, **nowsze > starsze**, **zatwierdzone > automatyczne**.

---

## Problem

Nie wszystkie dokumenty są równie ważne. W tradycyjnym RAG:

```
Pytanie: "Jaki jest budżet projektu?"

❌ Bez priorytetów:
- Fragment czatu WhatsApp (sprzed roku): "może 10k?"
- Losowa notatka: "budżet do ustalenia"
- Email z zatwierdzeniem (najnowszy): "Budżet 50k zatwierdzony"

System może wybrać czat lub notatkę zamiast oficjalnego maila!
```

**Problem:** Wyszukiwanie semantyczne zwraca **najbardziej podobne** dokumenty, nie **najważniejsze**.

---

## Rozwiązanie

Digital Twin używa **wielowymiarowego scoringu**:

```
final_score = similarity_weight × similarity + priority_weight × priority
```

Gdzie `priority` łączy:
1. **Typ dokumentu** — decyzje > notatki > email > czaty
2. **Aktualność** — nowsze dokumenty mają wyższą wagę
3. **Status zatwierdzenia** — przypięte i zatwierdzone wyżej

---

## Hierarchia typów dokumentów

```python
from src.rag.priority import DocumentType

class DocumentType(IntEnum):
    DECISION = 100     # Formalne decyzje, umowy, zatwierdzenia
    NOTE = 70          # Osobiste notatki, notatki ze spotkań
    EMAIL = 50         # Korespondencja email
    CONVERSATION = 30  # WhatsApp, Messenger, czaty
```

### Mapowanie source_type → DocumentType

| source_type | DocumentType | Waga |
|-------------|--------------|:----:|
| `note` z tagiem "decision" | DECISION | 100 |
| `note` | NOTE | 70 |
| `email` | EMAIL | 50 |
| `whatsapp` | CONVERSATION | 30 |
| `messenger` | CONVERSATION | 30 |

---

## Status zatwierdzenia

```python
from src.rag.priority import ApprovalStatus

class ApprovalStatus(IntEnum):
    PINNED = 50      # Przypięty przez użytkownika (najważniejszy)
    APPROVED = 30    # Zatwierdzony/zweryfikowany
    AUTOMATIC = 0    # Automatycznie zindeksowany (domyślny)
```

### Jak ustawić status?

W metadanych dokumentu:

```python
# Przy indeksowaniu
metadata = {
    "is_pinned": True,      # → PINNED (+50)
    "is_approved": True,    # → APPROVED (+30)
    # Oba False → AUTOMATIC (+0)
}
```

---

## Recency Score (aktualność)

Nowsze dokumenty są ważniejsze. Waga maleje liniowo z czasem:

```python
def calculate_recency_score(doc_date: datetime, max_days: int = 365) -> float:
    """
    Zwraca 1.0 dla dzisiejszego dokumentu,
    0.0 dla dokumentu starszego niż max_days.
    """
    days_old = (datetime.now() - doc_date).days
    return max(0.0, 1.0 - (days_old / max_days))
```

### Przykłady recency score

| Wiek dokumentu | max_days=365 | max_days=90 |
|----------------|:------------:|:-----------:|
| Dzisiaj | 1.00 | 1.00 |
| 1 tydzień | 0.98 | 0.92 |
| 1 miesiąc | 0.92 | 0.67 |
| 3 miesiące | 0.75 | 0.00 |
| 6 miesięcy | 0.50 | 0.00 |
| 1 rok | 0.00 | 0.00 |

---

## Formuła końcowa

### 1. Oblicz priority_score

```python
priority_score = (
    type_score +        # 30-100 (znormalizowane do 0-1)
    approval_score +    # 0-50 (znormalizowane do 0-1)
    recency_score       # 0-1
) / 3  # Średnia → 0-1
```

### 2. Oblicz final_score

```python
final_score = (
    PRIORITY_SIMILARITY_WEIGHT * similarity_score +
    PRIORITY_DOCUMENT_WEIGHT * priority_score
)
```

### Domyślne wagi

```bash
PRIORITY_SIMILARITY_WEIGHT=0.7  # 70% podobieństwo semantyczne
PRIORITY_DOCUMENT_WEIGHT=0.3    # 30% priorytet dokumentu
```

---

## Przykład działania

**Pytanie:** "Jaki jest budżet projektu Alpha?"

**Kandydaci z wyszukiwania semantycznego:**

| # | Dokument | similarity | type | recency | approved | priority | final |
|---|----------|:----------:|:----:|:-------:|:--------:|:--------:|:-----:|
| 1 | Chat "może 10k" | 0.92 | 0.30 | 0.20 | 0.00 | 0.17 | **0.69** |
| 2 | Notatka "budżet TBD" | 0.88 | 0.70 | 0.50 | 0.00 | 0.40 | **0.74** |
| 3 | Email "50k approved" | 0.85 | 0.50 | 0.95 | 0.30 | 0.58 | **0.77** |

**Wynik:** Email z zatwierdzeniem wygrywa mimo niższego similarity!

```
final_score = 0.7 × 0.85 + 0.3 × 0.58 = 0.595 + 0.174 = 0.77
```

---

## Użycie w kodzie

### Obliczanie priorytetu dokumentu

```python
from src.rag.priority import calculate_priority, DocumentType

# Oblicz priorytet
priority = calculate_priority(
    source_type="email",
    date="2024-12-15",
    is_pinned=False,
    is_approved=True
)

print(f"Type score: {priority.type_score}")       # 50 (EMAIL)
print(f"Recency score: {priority.recency_score}") # ~0.99
print(f"Approval score: {priority.approval_score}") # 30 (APPROVED)
print(f"Total priority: {priority.priority_score}") # ~0.60
```

### Wyszukiwanie z priorytetami

```python
from src.indexer import VectorStore

vs = VectorStore()

# Pobierz więcej kandydatów, przefiltruj z priorytetami
results = vs.search_with_priority(
    query="budżet projektu",
    top_k=5,       # Zwróć 5 najlepszych
    fetch_k=50,    # Pobierz 50 kandydatów do rankingu
)

for doc in results:
    print(f"{doc['filename']}")
    print(f"  Similarity: {doc['similarity']:.2f}")
    print(f"  Priority: {doc['priority']:.2f}")
    print(f"  Final: {doc['final_score']:.2f}")
```

### Ranking dokumentów

```python
from src.rag.priority import rank_documents

# Lista dokumentów z ich scorami
documents = [
    {"id": "1", "similarity": 0.92, "priority": 0.17},
    {"id": "2", "similarity": 0.88, "priority": 0.40},
    {"id": "3", "similarity": 0.85, "priority": 0.58},
]

# Przerankuj
ranked = rank_documents(
    documents,
    similarity_weight=0.7,
    priority_weight=0.3
)

# ranked[0] będzie dokumentem #3 (email z zatwierdzeniem)
```

---

## Konfiguracja

### Wagi w .env

```bash
# Proporcja similarity vs priority
PRIORITY_SIMILARITY_WEIGHT=0.7    # 0.0 - 1.0
PRIORITY_DOCUMENT_WEIGHT=0.3      # 0.0 - 1.0
# Suma powinna = 1.0

# Okno czasowe dla recency
PRIORITY_RECENCY_MAX_DAYS=365     # Po tym czasie recency_score = 0
```

### Przykładowe konfiguracje

#### Tradycyjne RAG (tylko podobieństwo)

```bash
PRIORITY_SIMILARITY_WEIGHT=1.0
PRIORITY_DOCUMENT_WEIGHT=0.0
```

#### Silne priorytetyzowanie typów

```bash
PRIORITY_SIMILARITY_WEIGHT=0.5
PRIORITY_DOCUMENT_WEIGHT=0.5
```

#### Preferuj świeże dokumenty

```bash
PRIORITY_RECENCY_MAX_DAYS=90  # 3 miesiące
# Dokumenty starsze niż 90 dni mają recency_score = 0
```

#### Preferuj starsze (archiwum)

```bash
PRIORITY_RECENCY_MAX_DAYS=3650  # 10 lat
# Wolniejszy decay, stare dokumenty nadal ważne
```

---

## Metadata w dokumentach

### Automatyczne wykrywanie kategorii

```python
# src/loaders/base.py

def _detect_category(self, content: str, filename: str) -> str:
    """Wykryj kategorię dokumentu."""
    content_lower = content.lower()

    # Wykryj decyzje
    decision_keywords = ["decyzja:", "postanowienie:", "zatwierdzam", "decision:"]
    if any(kw in content_lower for kw in decision_keywords):
        return "decision"

    # Domyślnie → kategoria z source_type
    return self.source_type
```

### Ręczne oznaczanie

Dodaj metadane w frontmatter (Markdown):

```markdown
---
category: decision
is_approved: true
---

# Decyzja: Wybór technologii dla projektu X

Postanawiamy użyć React + Node.js...
```

### Przypinanie dokumentów

```python
from src.indexer import VectorStore

vs = VectorStore()

# Przypnij dokument (najwyższy priorytet)
vs.update_metadata(
    document_id="uuid-of-document",
    updates={"is_pinned": True}
)
```

---

## Struktura danych

### DocumentPriority

```python
@dataclass
class DocumentPriority:
    type_score: float        # 0.30 - 1.00 (znormalizowane z 30-100)
    recency_score: float     # 0.00 - 1.00
    approval_score: float    # 0.00 - 0.50 (znormalizowane z 0-50)
    priority_score: float    # Połączony wynik 0.00 - 1.00
```

### RankedDocument

```python
@dataclass
class RankedDocument:
    document: dict           # Oryginalny dokument
    similarity_score: float  # Wynik podobieństwa
    priority_score: float    # Wynik priorytetu
    final_score: float       # Ważony wynik końcowy
```

---

## Troubleshooting

### Problem: Stare dokumenty wciąż dominują

```bash
# Skróć okno recency
PRIORITY_RECENCY_MAX_DAYS=90

# Lub zwiększ wagę priorytetu
PRIORITY_DOCUMENT_WEIGHT=0.5
```

### Problem: Decyzje nie są wykrywane

Sprawdź czy:
1. Dokument zawiera słowa kluczowe ("decyzja:", "decision:")
2. Lub ma frontmatter z `category: decision`

```python
# Debug kategorii
from src.loaders import TextLoader

loader = TextLoader()
docs = loader.load("./data/notes/")
for doc in docs:
    print(f"{doc.metadata['filename']}: {doc.metadata.get('document_category', 'unknown')}")
```

### Problem: Wszystkie dokumenty mają ten sam priorytet

Sprawdź czy metadane są prawidłowo zapisywane:

```python
from src.indexer import VectorStore

vs = VectorStore()
results = vs.search("test", top_k=5)

for r in results:
    print(f"{r['filename']}:")
    print(f"  source_type: {r.get('source_type')}")
    print(f"  document_category: {r.get('document_category')}")
    print(f"  is_pinned: {r.get('is_pinned')}")
    print(f"  is_approved: {r.get('is_approved')}")
```

---

## Powiązane

- **[FR-P0-4: Explainability](FR-P0-4-Explainability)** — zobacz rozbicie scoringu
- **[Konfiguracja](Konfiguracja)** — ustawienia wag
- **[API Reference](API-Reference)** — dokumentacja calculate_priority

---

<p align="center">
  <a href="FR-P0-2-Offline-Mode">← FR-P0-2: Offline Mode</a> |
  <a href="Home">Strona główna</a> |
  <a href="FR-P0-4-Explainability">FR-P0-4: Explainability →</a>
</p>
