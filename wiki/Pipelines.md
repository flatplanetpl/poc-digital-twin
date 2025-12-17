# Pipeline'y przetwarzania

Szczegółowy opis przepływu danych przez system Digital Twin — od pliku źródłowego do odpowiedzi z cytatami.

---

## Przegląd architektury

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              DIGITAL TWIN                                      │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ╔════════════════════╗       ╔════════════════════╗                          │
│  ║  PIPELINE INDEXING ║       ║  PIPELINE QUERY    ║                          │
│  ╠════════════════════╣       ╠════════════════════╣                          │
│  ║                    ║       ║                    ║                          │
│  ║  Files → Loader    ║       ║  Question          ║                          │
│  ║  (9 loaders)       ║       ║       ↓            ║                          │
│  ║       ↓            ║       ║  QueryPreprocessor ║   ← NEW: filter extract  │
│  ║  Chunking          ║       ║       ↓            ║                          │
│  ║       ↓            ║       ║  Embedding         ║                          │
│  ║  Metadata          ║       ║       ↓            ║                          │
│  ║       ↓            ║       ║  Retrieval +       ║                          │
│  ║  Embedding         ║       ║  MetadataFilters   ║   ← NEW: person/date     │
│  ║       ↓            ║       ║       ↓            ║                          │
│  ║  Qdrant Store      ║       ║  Priority Rank     ║                          │
│  ║       ↓            ║       ║       ↓            ║                          │
│  ║  ContactRegistry   ║   ←   ║  Context Build     ║                          │
│  ║                    ║   │   ║       ↓            ║                          │
│  ╚════════════════════╝   │   ║  LLM Generate      ║                          │
│                           │   ║       ↓            ║                          │
│  ╔════════════════════╗   │   ║  Citation Extract  ║                          │
│  ║  CONTACT GRAPH     ║◄──┘   ║       ↓            ║                          │
│  ╠════════════════════╣       ║  Response          ║                          │
│  ║  ContactRegistry   ║       ╚════════════════════╝                          │
│  ║       ↓            ║                                                       │
│  ║  Relationships     ║       ╔════════════════════╗                          │
│  ║       ↓            ║       ║  PIPELINE DELETE   ║                          │
│  ║  Interaction Score ║       ╠════════════════════╣                          │
│  ║       ↓            ║       ║  Request → Lookup  ║                          │
│  ║  Topic Analysis    ║       ║       ↓            ║                          │
│  ╚════════════════════╝       ║  Delete Vectors    ║                          │
│                               ║       ↓            ║                          │
│                               ║  Purge History     ║                          │
│                               ║       ↓            ║                          │
│                               ║  Update Registry   ║                          │
│                               ║       ↓            ║                          │
│                               ║  Audit Log         ║                          │
│                               ╚════════════════════╝                          │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline 1: Indexing (Import danych)

Pipeline indeksowania przekształca pliki źródłowe w przeszukiwalne wektory.

### Diagram przepływu

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FILES     │────►│   LOADER    │────►│   CHUNKER   │────►│  METADATA   │
│             │     │             │     │             │     │   ENRICH    │
│ .txt .md    │     │ TextLoader  │     │ 512 tokens  │     │ + UUID      │
│ .eml .mbox  │     │ EmailLoader │     │ 50 overlap  │     │ + category  │
│ .txt (WA)   │     │ WhatsApp    │     │             │     │ + priority  │
│ .json (FB)  │     │ Messenger   │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  REGISTRY   │◄────│   QDRANT    │◄────│  EMBEDDING  │◄────│   NODES     │
│             │     │             │     │             │     │             │
│ SQLite      │     │ Vectors +   │     │ all-MiniLM  │     │ LlamaIndex  │
│ doc_id      │     │ Metadata    │     │ 384 dims    │     │ TextNode    │
│ hash        │     │             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Krok 1: Loading (Parsowanie plików)

```python
# src/loaders/base.py

class BaseLoader(ABC):
    """Template Method Pattern — szkielet loadera."""

    def load(self, directory: Path) -> list[Document]:
        """Główna metoda — wywołuje hook'i."""
        files = self._find_files(directory)      # Hook 1
        documents = []
        for file in files:
            content = self._parse_file(file)      # Hook 2
            metadata = self._extract_metadata(file, content)  # Hook 3
            documents.append(Document(content, metadata))
        return documents

    @abstractmethod
    def _parse_file(self, path: Path) -> str:
        """Subklasy implementują parsowanie."""
        pass
```

**Loadery:**

| Loader | Formaty | Parsowanie |
|--------|---------|------------|
| `TextLoader` | .txt, .md | Bezpośredni odczyt + frontmatter |
| `EmailLoader` | .eml, .mbox | `email.parser` + nagłówki |
| `WhatsAppLoader` | .txt | Regex na format eksportu |
| `MessengerLoader` | .json | JSON Facebook export + thread detection |
| `ProfileLoader` | .json | Profil użytkownika Facebook |
| `ContactsLoader` | .json | Lista znajomych + kontakty telefonu |
| `LocationLoader` | .json | Historia lokalizacji |
| `SearchHistoryLoader` | .json | Historia wyszukiwania |
| `AdsInterestsLoader` | .json | Zainteresowania reklamowe |

### Krok 2: Chunking (Podział na fragmenty)

```python
# Konfiguracja
CHUNK_SIZE = 512      # ~128 tokenów
CHUNK_OVERLAP = 50    # Zachowanie kontekstu

# LlamaIndex SentenceSplitter
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)

nodes = splitter.get_nodes_from_documents(documents)
```

**Efekt:**
```
Dokument 2000 znaków → 4 chunki po ~500 znaków
                       (z 50 znaków nakładania)
```

### Krok 3: Metadata Enrichment

```python
# src/loaders/base.py

def _create_metadata(self, file_path, content) -> dict:
    """Tworzy metadane dla dokumentu."""
    doc_id = str(uuid.uuid4())

    return {
        # Identyfikacja
        "document_id": doc_id,
        "filename": file_path.name,
        "file_path": str(file_path),

        # Typ i kategoria
        "source_type": self.source_type,  # "email", "note", etc.
        "document_category": self._detect_category(content),

        # Data
        "date": self._extract_date(file_path, content),
        "indexed_at": datetime.now().isoformat(),

        # Priorytet (FR-P0-3)
        "is_pinned": False,
        "is_approved": False,

        # Dodatkowe (per loader)
        "sender": ...,  # EmailLoader
        "recipient": ...,
        "subject": ...,
    }
```

### Krok 4: Embedding

```python
# Model: sentence-transformers/all-MiniLM-L6-v2
# Wymiary: 384
# Czas: ~10ms per chunk

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Wektoryzacja tekstu
vector = embed_model.get_text_embedding(chunk_text)
# vector.shape = (384,)
```

### Krok 5: Storage (Qdrant)

```python
# src/indexer/vector_store.py

def add_documents(self, documents: list[Document]) -> int:
    """Dodaj dokumenty do Qdrant."""

    # LlamaIndex pipeline
    nodes = self._chunk_documents(documents)

    for node in nodes:
        # 1. Oblicz embedding
        vector = self.embed_model.get_text_embedding(node.text)

        # 2. Zapisz w Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[{
                "id": node.node_id,
                "vector": vector,
                "payload": node.metadata,
            }]
        )

    return len(nodes)
```

### Krok 6: Registry (Śledzenie)

```python
# src/storage/document_registry.py

def register_document(self, file_path, source_type, chunk_count, metadata):
    """Rejestruj dokument do śledzenia."""

    content_hash = self._compute_hash(file_path)

    # INSERT INTO documents
    self.conn.execute("""
        INSERT INTO documents
        (document_id, file_path, content_hash, source_type,
         chunk_count, status, indexed_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?)
    """, (metadata["document_id"], str(file_path), content_hash,
          source_type, chunk_count, datetime.now()))
```

---

## Pipeline 2: Query (Zapytania)

Pipeline zapytania przekształca pytanie użytkownika w uziemioną odpowiedź z cytatami.

### Diagram przepływu

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  QUESTION   │────►│   QUERY     │────►│  EMBEDDING  │────►│   QDRANT    │
│             │     │ PREPROCESSOR│     │             │     │   SEARCH    │
│ "Co Ewa     │     │             │     │ all-MiniLM  │     │             │
│  mówiła?"   │     │ extract:    │     │ 384 dims    │     │ + metadata  │
│             │     │ - person    │     │             │     │   filters   │
│             │     │ - date      │     │             │     │             │
│             │     │ - source    │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RESPONSE   │◄────│  CITATION   │◄────│    LLM      │◄────│  PRIORITY   │
│             │     │  EXTRACT    │     │  GENERATE   │     │   RANKING   │
│ answer +    │     │             │     │             │     │             │
│ citations + │     │ [Source:...]│     │ GPT4All /   │     │ sim*0.7 +   │
│ explanation │     │             │     │ OpenAI      │     │ pri*0.3     │
│ + filters   │     │             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Krok 1: Query Preprocessing (NEW)

```python
# src/rag/query_preprocessor.py

class QueryPreprocessor:
    """Ekstrakcja filtrów z języka naturalnego."""

    PERSON_PATTERNS = [
        r"(?:from|by|with|od|z)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:powiedział|napisał|wspomniał)\s+([A-Z][a-z]+)",
    ]

    DATE_PATTERNS = [
        (r"(?:in|w)\s+(\w+)\s+(\d{4})", "month_year"),
        (r"(?:last|w zeszłym)\s+(week|month|year|tygodniu|miesiącu|roku)", "relative"),
    ]

    def preprocess(self, query: str) -> PreprocessedQuery:
        """Wyciągnij filtry z zapytania."""
        return PreprocessedQuery(
            clean_query="co mówiła?",        # zapytanie bez filtrów
            person_filter="Ewa",              # wyciągnięta osoba
            date_range=(start, end),          # zakres dat
            source_filter="messenger",        # typ źródła
            extracted_filters={"person": "Ewa", ...},
        )
```

**Przykłady:**
- `"Co Ewa mówiła o wakacjach?"` → `person_filter="Ewa"`
- `"Maile od Jana w grudniu 2023"` → `person_filter="Jan"`, `date_range=(2023-12-01, 2023-12-31)`, `source_filter="email"`
- `"Wiadomości z WhatsApp"` → `source_filter="whatsapp"`

### Krok 2: Query Embedding

```python
# Wektoryzacja pytania (ten sam model co dokumenty!)
query_vector = embed_model.get_text_embedding(clean_question)
```

### Krok 3: Vector Search (Qdrant) + Metadata Filtering

```python
# Wyszukiwanie z filtrami metadanych
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

filters = MetadataFilters(filters=[
    MetadataFilter(key="sender", value="Ewa", operator="contains"),
    MetadataFilter(key="source_type", value="messenger", operator="eq"),
])

results = self.client.search(
    collection_name=self.collection_name,
    query_vector=query_vector,
    limit=fetch_k,  # Pobierz więcej dla re-rankingu
    query_filter=filters,  # Qdrant metadata filter
    with_payload=True,
)
```

### Krok 4: Priority Re-ranking (FR-P0-3)

```python
# src/indexer/vector_store.py

def search_with_priority(self, query, top_k=5, fetch_k=50):
    """Wyszukaj z re-rankingiem priorytetów."""

    # 1. Pobierz więcej kandydatów
    candidates = self._raw_search(query, limit=fetch_k)

    # 2. Oblicz priority dla każdego
    for doc in candidates:
        doc["priority"] = calculate_priority(
            source_type=doc["source_type"],
            date=doc["date"],
            is_pinned=doc["is_pinned"],
            is_approved=doc["is_approved"],
        ).priority_score

    # 3. Oblicz final_score
    for doc in candidates:
        doc["final_score"] = (
            settings.priority_similarity_weight * doc["similarity"] +
            settings.priority_document_weight * doc["priority"]
        )

    # 4. Posortuj i zwróć top_k
    ranked = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    return ranked[:top_k]
```

### Krok 5: Context Building

```python
# src/rag/query_engine.py

def _build_context(self, source_nodes):
    """Zbuduj kontekst dla LLM."""

    context_parts = []
    for node in source_nodes:
        # Formatuj fragment z metadanymi
        part = f"""
---
Source: {node.metadata['source_type']}
File: {node.metadata['filename']}
Date: {node.metadata['date']}
---
{node.text}
"""
        context_parts.append(part)

    return "\n".join(context_parts)
```

### Krok 6: LLM Generation

```python
# Grounded System Prompt
SYSTEM_PROMPT = """
Jesteś osobistym asystentem danych. TYLKO na podstawie kontekstu.

ZASADY:
1. TYLKO informacje z kontekstu
2. Jeśli nie ma: "Nie znaleziono..."
3. ZAWSZE cytuj: [Źródło: {typ}, {data}, "{fragment}"]

Kontekst:
{context_str}

Pytanie: {query_str}
"""

# LlamaIndex RetrieverQueryEngine
response = query_engine.query(question)
answer = str(response)
```

### Krok 7: Citation Extraction

```python
# src/rag/citations.py

def extract_citations(source_nodes) -> list[Citation]:
    """Wyciągnij cytaty z odpowiedzi."""

    citations = []
    for node in source_nodes:
        citations.append(Citation(
            document_id=node.metadata["document_id"],
            source_type=node.metadata["source_type"],
            filename=node.metadata["filename"],
            date=node.metadata.get("date", "unknown"),
            fragment=node.text[:100] + "..." if len(node.text) > 100 else node.text,
            score=node.score or 0.0,
        ))

    return citations
```

### Krok 8: Response Assembly

```python
# Złożenie odpowiedzi
result = {
    "answer": answer,
    "sources": [c.to_dict() for c in citations],
    "citations": citations,
    "is_grounded": validate_grounding(answer, citations),
    "no_context_found": not citations,
    "query_time_ms": (time.time() - start) * 1000,
    "filters_applied": {"person": "Ewa", "source": "messenger"},  # NEW
}

if include_explanation:
    result["explanation"] = self._build_explanation(...)

return result
```

---

## Pipeline 3: Contact Graph (NEW)

Pipeline Contact Graph buduje i analizuje relacje między kontaktami.

### Diagram przepływu

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INDEXED    │────►│  CONTACT    │────►│  CONTACT    │
│  MESSAGES   │     │  REGISTRY   │     │   GRAPH     │
│             │     │             │     │             │
│ Messenger   │     │ SQLite DB   │     │ Relationships│
│ WhatsApp    │     │ name, source│     │ Scores      │
│ Email       │     │ stats       │     │ Topics      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Krok 1: ContactRegistry (SQLite)

```python
# src/storage/contact_registry.py

class ContactRegistry:
    """Śledzenie kontaktów z różnych źródeł."""

    def register_contact(self, name, source, timestamp, relationship_type, metadata):
        """Zarejestruj/aktualizuj kontakt."""
        # INSERT OR UPDATE INTO contacts
        # Normalizuje imię: "Jan Kowalski" -> "jan kowalski"

    def update_stats(self, name, source, message_count, timestamp):
        """Aktualizuj statystyki interakcji."""
        # UPDATE contact_interactions (monthly aggregation)

    def get_top_contacts(self, limit=10, source=None):
        """Zwróć najczęstsze kontakty."""
        # ORDER BY total_interactions DESC
```

### Krok 2: ContactGraph Service

```python
# src/graph/contact_graph.py

@dataclass
class ContactRelationship:
    contact_name: str
    message_count: int
    first_interaction: datetime
    last_interaction: datetime
    interaction_score: float  # 0-1
    sources: list[str]  # ['messenger', 'whatsapp']

class ContactGraph:
    def build_from_registry(self) -> int:
        """Zbuduj graf z ContactRegistry."""

    def calculate_interaction_score(self, relationship) -> float:
        """
        score = 0.4 * frequency + 0.4 * recency + 0.2 * diversity
        - frequency: messages_per_month / 100 (capped at 0.4)
        - recency: 1 - (days_since_last / 365)
        - diversity: 0.2 if multiple sources
        """

    def get_top_contacts(self, limit=10) -> list[ContactRelationship]:
        """Zwróć najważniejsze relacje."""

    def find_contacts_by_topic(self, topic: str, top_k=5) -> list[tuple[str, float]]:
        """Znajdź kontakty rozmawiające o danym temacie."""
```

### Przykłady użycia

```python
# Kto jest moim najczęstszym rozmówcą?
graph = ContactGraph(contact_registry, vector_store)
top = graph.get_top_contacts(limit=5)
# [ContactRelationship(name="Ewa", score=0.87), ...]

# Z kim rozmawiam o pracy?
work_contacts = graph.find_contacts_by_topic("praca projekt deadline")
# [("Jan", 0.92), ("Maria", 0.78)]
```

---

## Pipeline 4: Delete (Usuwanie)

Pipeline usuwania gwarantuje kompletne usunięcie danych ze wszystkich systemów.

### Diagram przepływu

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   REQUEST   │────►│   LOOKUP    │────►│   DELETE    │
│             │     │             │     │   QDRANT    │
│ document_id │     │ Registry    │     │             │
│ or sender   │     │ find docs   │     │ vectors     │
│ or filter   │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   AUDIT     │◄────│   UPDATE    │◄────│   PURGE     │
│    LOG      │     │  REGISTRY   │     │  HISTORY    │
│             │     │             │     │             │
│ operation   │     │ status =    │     │ remove      │
│ entity_id   │     │ "deleted"   │     │ references  │
│ reason      │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Krok 1: Lookup

```python
# Znajdź dokumenty do usunięcia
if document_id:
    docs = [registry.get_by_id(document_id)]
elif sender:
    docs = vector_store.search("", filters={"sender": sender})
elif source_type:
    docs = vector_store.search("", filters={"source_type": source_type})
```

### Krok 2: Delete from Qdrant

```python
# src/indexer/vector_store.py

def delete_document(self, document_id: str) -> bool:
    """Usuń wszystkie wektory dokumentu."""

    self.client.delete(
        collection_name=self.collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        )
    )
    return True
```

### Krok 3: Purge from History

```python
# src/storage/chat_history.py

def purge_by_document(self, document_id: str) -> int:
    """Usuń referencje z historii czatów."""

    # Znajdź wiadomości z tym źródłem
    cursor = self.conn.execute("""
        UPDATE messages
        SET sources = json_remove(sources, ?)
        WHERE json_extract(sources, ?) IS NOT NULL
    """, (f'$."{document_id}"', f'$."{document_id}"'))

    return cursor.rowcount
```

### Krok 4: Update Registry

```python
# src/storage/document_registry.py

def mark_deleted(self, document_id: str) -> bool:
    """Oznacz dokument jako usunięty."""

    self.conn.execute("""
        UPDATE documents
        SET status = 'deleted', deleted_at = ?
        WHERE document_id = ?
    """, (datetime.now(), document_id))

    return True
```

### Krok 5: Audit Log

```python
# src/storage/audit.py

def log_delete(self, document_id, reason, chunks_deleted):
    """Zaloguj operację usunięcia."""

    self.log(
        operation="delete",
        entity_type="document",
        entity_id=document_id,
        details={
            "reason": reason,
            "chunks_deleted": chunks_deleted,
            "timestamp": datetime.now().isoformat(),
        }
    )
```

---

## Timing i wydajność

### Typowe czasy operacji

| Operacja | Czas | Czynniki |
|----------|:----:|----------|
| Embedding (per chunk) | ~10ms | Model, GPU |
| Qdrant search | ~50ms | Rozmiar indeksu |
| Priority ranking | ~5ms | fetch_k |
| Context building | ~2ms | top_k |
| LLM generation (GPT4All) | 1-5s | Model, kontekst |
| LLM generation (OpenAI) | 0.5-2s | Model, kontekst |

### Optymalizacje

```bash
# Szybszy retrieval
TOP_K=3              # Mniej dokumentów

# Szybsze embeddingi
# Użyj GPU jeśli dostępne

# Szybsze LLM
LLM_PROVIDER=openai  # Chmura szybsza niż lokalne
# lub mniejszy model lokalny:
GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf
```

---

## Powiązane

- **[FR-P0-3: Priority Rules](FR-P0-3-Priority-Rules)** — szczegóły re-rankingu
- **[FR-P0-4: Explainability](FR-P0-4-Explainability)** — jak zobaczyć co się dzieje
- **[API Reference](API-Reference)** — dokumentacja klas

---

<p align="center">
  <a href="FR-P0-5-Forget-RTBF">← FR-P0-5: Forget/RTBF</a> |
  <a href="Home">Strona główna</a> |
  <a href="Scenariusze-użycia">Scenariusze użycia →</a>
</p>
