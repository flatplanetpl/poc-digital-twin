# FR-P0-5: Forget / RTBF

**Status:** ✅ Zaimplementowane (v1.0)

Prawo do bycia zapomnianym — **kompletne usuwanie danych** ze wszystkich systemów, zgodne z RODO.

---

## Problem

RODO (GDPR) wymaga "prawa do bycia zapomnianym" (Right To Be Forgotten). W systemie RAG dane mogą być w wielu miejscach:

```
Gdzie są moje dane?
├── Qdrant (wektory embeddingów)
├── SQLite - chat_history (referencje w odpowiedziach)
├── SQLite - document_registry (metadane)
└── Pliki źródłowe (opcjonalnie)
```

**Problem:** Usunięcie z jednego miejsca to nie wszystko!

---

## Rozwiązanie

**ForgetService** — orchestrator usuwania ze wszystkich systemów:

```python
from src.rag import ForgetService

forget = ForgetService(...)

# Jeden call → usunięte wszędzie
result = forget.forget_document(
    document_id="uuid-...",
    reason="RODO - żądanie użytkownika"
)
```

---

## Co jest usuwane?

| Komponent | Co usuwane | Jak |
|-----------|------------|-----|
| **Qdrant** | Wektory embeddingów | `delete_document()` |
| **ChatHistory** | Referencje do źródeł | `purge_by_document()` |
| **DocumentRegistry** | Status → "deleted" | `mark_deleted()` |
| **AuditLog** | Wpis o usunięciu | `log_delete()` |

### Co NIE jest usuwane automatycznie?

- **Pliki źródłowe** — musisz usunąć ręcznie
- **Backupy** — sprawdź swoje kopie zapasowe
- **Cache** — automatycznie wygasa

---

## Użycie w kodzie

### Inicjalizacja ForgetService

```python
from src.rag import ForgetService
from src.indexer import VectorStore
from src.storage import ChatHistory, DocumentRegistry, AuditLogger

forget = ForgetService(
    vector_store=VectorStore(),
    chat_history=ChatHistory(),
    document_registry=DocumentRegistry(),
    audit_logger=AuditLogger()  # Opcjonalny
)
```

### Usunięcie pojedynczego dokumentu

```python
# Znajdź ID dokumentu
from src.indexer import VectorStore

vs = VectorStore()
results = vs.search("dokument do usunięcia", top_k=1)
document_id = results[0]["document_id"]

# Usuń
result = forget.forget_document(
    document_id=document_id,
    reason="Życzenie użytkownika"
)

print(f"✅ Usunięto:")
print(f"   Wektory: {result.vectors_deleted}")
print(f"   Referencje: {result.references_deleted}")
print(f"   Dokumenty w rejestrze: {result.documents_deleted}")
print(f"   Razem: {result.total_deleted}")
```

### Usunięcie po nadawcy (RODO)

```python
# Usuń wszystkie e-maile od osoby
result = forget.forget_sender(
    sender="jan.kowalski@example.com",
    reason="RODO Art. 17 - żądanie usunięcia"
)

print(f"Usunięto {result.total_deleted} elementów od {sender}")
```

### Usunięcie po typie źródła

```python
# Usuń wszystkie czaty WhatsApp
result = forget.forget_by_source_type(
    source_type="whatsapp",
    reason="Rezygnacja z synchronizacji"
)

# Usuń wszystkie wiadomości Messenger
result = forget.forget_by_source_type(
    source_type="messenger",
    reason="Usunięcie konta FB"
)
```

---

## ForgetResult — struktura wyniku

```python
@dataclass
class ForgetResult:
    success: bool              # Czy operacja się powiodła
    vectors_deleted: int       # Usunięte wektory z Qdrant
    references_deleted: int    # Usunięte referencje z ChatHistory
    documents_deleted: int     # Zaktualizowane wpisy w Registry
    total_deleted: int         # Suma wszystkich
    timestamp: datetime        # Czas operacji
    reason: str                # Powód (do audytu)
    audit_id: int | None       # ID wpisu w logu audytu
```

### Przykład użycia wyniku

```python
result = forget.forget_sender("klient@firma.pl", "RODO")

if result.success:
    print(f"""
📋 Raport usunięcia danych
━━━━━━━━━━━━━━━━━━━━━━━━━━
Data: {result.timestamp}
Powód: {result.reason}

Usunięto:
  • Wektory: {result.vectors_deleted}
  • Referencje w historii: {result.references_deleted}
  • Wpisy w rejestrze: {result.documents_deleted}
  ─────────────────────────
  RAZEM: {result.total_deleted}

ID audytu: {result.audit_id}
""")
else:
    print("❌ Operacja nie powiodła się")
```

---

## Metody VectorStore

### delete_document

```python
from src.indexer import VectorStore

vs = VectorStore()

# Usuń po ID dokumentu
success = vs.delete_document("550e8400-e29b-41d4-a716-446655440000")

if success:
    print("Wektory usunięte z Qdrant")
```

### delete_by_filter

```python
# Usuń wszystkie dokumenty pasujące do filtru
deleted_count = vs.delete_by_filter({
    "sender": "spam@example.com"
})
print(f"Usunięto {deleted_count} dokumentów")

# Usuń po typie
deleted_count = vs.delete_by_filter({
    "source_type": "whatsapp"
})

# Usuń po zakresie dat (wymaga rozszerzenia)
deleted_count = vs.delete_by_filter({
    "date_before": "2023-01-01"
})
```

---

## Metody ChatHistory

### purge_by_document

```python
from src.storage import ChatHistory

history = ChatHistory()

# Usuń wszystkie referencje do dokumentu z odpowiedzi
deleted = history.purge_by_document("uuid-dokumentu")
print(f"Usunięto {deleted} referencji z historii czatów")
```

### purge_by_entity

```python
# Usuń referencje po nadawcy
deleted = history.purge_by_entity(
    entity_type="sender",
    entity_value="jan.kowalski@example.com"
)

# Usuń referencje po typie źródła
deleted = history.purge_by_entity(
    entity_type="source_type",
    entity_value="messenger"
)
```

---

## Audyt operacji

Każde usunięcie jest logowane (jeśli `AUDIT_ENABLED=true`):

```python
from src.storage import AuditLogger

audit = AuditLogger()

# Podgląd ostatnich usunięć
entries = audit.get_entries(
    operation_type="delete",
    limit=10
)

for entry in entries:
    print(f"""
{entry.timestamp}
  Operacja: {entry.operation}
  Typ: {entry.entity_type}
  ID: {entry.entity_id}
  Szczegóły: {entry.details}
""")
```

### Struktura wpisu audytu

```python
@dataclass
class AuditEntry:
    id: int
    timestamp: datetime
    operation: str        # "delete"
    entity_type: str      # "document", "sender", "source_type"
    entity_id: str        # ID lub wartość
    details: dict         # {"reason": "...", "count": N}
```

---

## Scenariusze użycia

### Scenariusz 1: Żądanie RODO od osoby

```python
# 1. Zidentyfikuj wszystkie dane osoby
sender = "jan.kowalski@example.com"

# 2. Sprawdź ile dokumentów
from src.indexer import VectorStore
vs = VectorStore()
docs = vs.search("", filters={"sender": sender}, top_k=1000)
print(f"Znaleziono {len(docs)} dokumentów od {sender}")

# 3. Potwierdź z użytkownikiem
confirm = input(f"Usunąć {len(docs)} dokumentów? [y/N]: ")
if confirm.lower() != 'y':
    print("Anulowano")
    exit()

# 4. Usuń
result = forget.forget_sender(sender, "RODO Art. 17")

# 5. Wygeneruj raport
print(f"""
RAPORT USUNIĘCIA DANYCH - RODO Art. 17
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Podmiot danych: {sender}
Data realizacji: {result.timestamp}
ID audytu: {result.audit_id}

Usunięto:
- Wektory embeddingów: {result.vectors_deleted}
- Referencje w historii: {result.references_deleted}
- Wpisy w rejestrze: {result.documents_deleted}

UWAGA: Sprawdź pliki źródłowe i backupy ręcznie.
""")
```

### Scenariusz 2: Usunięcie wrażliwego dokumentu

```python
# Przypadkowo zindeksowałeś wrażliwy dokument
document_id = "uuid-wrażliwego-dokumentu"

# Natychmiastowe usunięcie
result = forget.forget_document(
    document_id=document_id,
    reason="Przypadkowe zindeksowanie wrażliwego dokumentu"
)

# Sprawdź czy naprawdę usunięte
vs = VectorStore()
check = vs.search("", filters={"document_id": document_id})
if not check:
    print("✅ Dokument całkowicie usunięty z systemu")
```

### Scenariusz 3: Rezygnacja z platformy

```python
# Użytkownik rezygnuje z synchronizacji WhatsApp
result = forget.forget_by_source_type(
    source_type="whatsapp",
    reason="Rezygnacja z synchronizacji WhatsApp"
)

print(f"Usunięto {result.total_deleted} wiadomości WhatsApp")

# Opcjonalnie: usuń też pliki źródłowe
import shutil
shutil.rmtree("./data/whatsapp/")
```

### Scenariusz 4: Pełne czyszczenie systemu

```python
# UWAGA: Usuwa WSZYSTKIE dane!
from src.indexer import VectorStore

vs = VectorStore()

# Metoda 1: Usuń kolekcję
vs.delete_collection()

# Metoda 2: Usuń per-typ
for source_type in ["note", "email", "whatsapp", "messenger"]:
    result = forget.forget_by_source_type(source_type, "Pełne czyszczenie")
    print(f"{source_type}: {result.total_deleted}")

# Metoda 3: Nowy indeks
python scripts/ingest.py --reset
```

---

## Konfiguracja

### Włączanie audytu

```bash
# .env
AUDIT_ENABLED=true
AUDIT_QUERIES=false  # Nie loguj zapytań, tylko operacje
```

### Soft delete vs hard delete

Obecnie system używa **hard delete** — dane są faktycznie usuwane.

W przyszłości planowany **soft delete**:
```python
# Soft delete — oznacz jako usunięte, zachowaj
vs.soft_delete(document_id)  # status = "deleted"

# Hard delete — faktyczne usunięcie
vs.hard_delete(document_id)  # fizyczne usunięcie
```

---

## Bezpieczeństwo

### Co jest logowane?

| Pole | Wartość |
|------|---------|
| timestamp | Czas operacji |
| operation | "delete" |
| entity_type | "document", "sender", "source_type" |
| entity_id | ID dokumentu lub wartość filtra |
| details.reason | Powód usunięcia |
| details.count | Liczba usuniętych elementów |

### Co NIE jest logowane?

- ❌ Treść dokumentu
- ❌ Treść odpowiedzi
- ❌ Szczegółowe metadane

---

## Troubleshooting

### Problem: "Document not found"

```python
# Sprawdź czy dokument istnieje
vs = VectorStore()
results = vs.search("", filters={"document_id": doc_id})

if not results:
    print("Dokument nie istnieje lub już usunięty")
```

### Problem: Referencje pozostają w historii

```python
# Ręczne oczyszczenie
from src.storage import ChatHistory

history = ChatHistory()

# Wyczyść wszystkie wiadomości z tym źródłem
deleted = history.purge_by_document(document_id)
print(f"Ręcznie usunięto {deleted} referencji")
```

### Problem: Audyt nie działa

```bash
# Sprawdź konfigurację
cat .env | grep AUDIT

# Powinno być:
# AUDIT_ENABLED=true
```

---

## Powiązane

- **[FR-P0-2: Offline Mode](FR-P0-2-Offline-Mode)** — zapobieganie wyciekom danych
- **[Konfiguracja](Konfiguracja)** — ustawienia audytu
- **[API Reference](API-Reference)** — pełna dokumentacja ForgetService

---

<p align="center">
  <a href="FR-P0-4-Explainability">← FR-P0-4: Explainability</a> |
  <a href="Home">Strona główna</a> |
  <a href="Pipelines">Pipelines →</a>
</p>
