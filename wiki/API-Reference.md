# API Reference

Kompletna dokumentacja programistyczna głównych klas i funkcji Digital Twin.

---

## Spis treści

1. [RAGEngine](#ragengine)
2. [VectorStore](#vectorstore)
3. [ForgetService](#forgetservice)
4. [ChatHistory](#chathistory)
5. [DocumentRegistry](#documentregistry)
6. [AuditLogger](#auditlogger)
7. [LLM Factory](#llm-factory)
8. [Priority System](#priority-system)
9. [Citations](#citations)
10. [Explainability](#explainability)

---

## RAGEngine

Główna klasa do interakcji z systemem RAG.

**Lokalizacja:** `src/rag/query_engine.py`

### Konstruktor

```python
class RAGEngine:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        llm_provider: BaseLLM | None = None,
        chat_history: ChatHistory | None = None,
    ):
        """
        Inicjalizacja RAG engine.

        Args:
            vector_store: Instancja VectorStore. Jeśli None, tworzy nową.
            llm_provider: Dostawca LLM. Jeśli None, tworzy z ustawień.
            chat_history: Historia czatów. Jeśli None, tworzy nową.
        """
```

### Metody

#### query()

```python
def query(
    self,
    question: str,
    conversation_id: int | None = None,
    top_k: int | None = None,
    include_sources: bool = True,
    include_explanation: bool = False,
) -> dict:
    """
    Wykonaj zapytanie RAG z uziemionymi odpowiedziami.

    Args:
        question: Pytanie użytkownika
        conversation_id: ID konwersacji dla kontekstu (opcjonalne)
        top_k: Liczba dokumentów do pobrania (domyślnie z config)
        include_sources: Czy dołączyć metadane źródeł
        include_explanation: Czy dołączyć wyjaśnienie RAG (FR-P0-4)

    Returns:
        dict z kluczami:
            - answer (str): Wygenerowana odpowiedź
            - sources (list[dict]): Metadane źródeł
            - citations (list[dict]): Strukturalne cytaty
            - is_grounded (bool): Czy odpowiedź jest uziemiona
            - no_context_found (bool): Czy nie znaleziono kontekstu
            - conversation_id (int|None): ID konwersacji
            - query_time_ms (float): Czas zapytania w ms
            - explanation (dict|None): Wyjaśnienie RAG (jeśli requested)

    Example:
        >>> engine = RAGEngine()
        >>> result = engine.query("Kiedy mam spotkanie?")
        >>> print(result["answer"])
    """
```

#### search()

```python
def search(
    self,
    query: str,
    top_k: int | None = None,
    source_type: str | None = None,
) -> list[dict]:
    """
    Wyszukaj dokumenty bez generowania odpowiedzi.

    Args:
        query: Zapytanie wyszukiwania
        top_k: Liczba wyników (domyślnie z config)
        source_type: Filtr po typie źródła (opcjonalne)

    Returns:
        Lista dokumentów z metadanymi:
            - document_id (str)
            - filename (str)
            - source_type (str)
            - content (str): Fragment tekstu
            - score (float): Wynik podobieństwa

    Example:
        >>> results = engine.search("umowa", source_type="email")
        >>> for doc in results:
        ...     print(f"{doc['filename']}: {doc['score']:.2f}")
    """
```

#### set_llm_provider()

```python
def set_llm_provider(self, provider: str | BaseLLM) -> None:
    """
    Zmień dostawcę LLM.

    Args:
        provider: Nazwa providera ("gpt4all", "openai", "anthropic")
                  lub instancja BaseLLM

    Raises:
        OfflineModeError: Jeśli cloud provider w trybie offline

    Example:
        >>> engine.set_llm_provider("openai")
        >>> engine.set_llm_provider(my_custom_llm)
    """
```

#### get_stats()

```python
def get_stats(self) -> dict:
    """
    Pobierz statystyki systemu.

    Returns:
        dict:
            - index (dict): Statystyki indeksu Qdrant
            - llm_provider (dict): Info o aktualnym LLM

    Example:
        >>> stats = engine.get_stats()
        >>> print(f"Dokumentów: {stats['index']['points_count']}")
    """
```

---

## VectorStore

Interfejs do bazy wektorowej Qdrant.

**Lokalizacja:** `src/indexer/vector_store.py`

### Konstruktor

```python
class VectorStore:
    def __init__(
        self,
        collection_name: str | None = None,
        embedding_model: str | None = None,
    ):
        """
        Inicjalizacja store'a wektorowego.

        Args:
            collection_name: Nazwa kolekcji (domyślnie z config)
            embedding_model: Model embeddingów (domyślnie z config)
        """
```

### Metody

#### add_documents()

```python
def add_documents(self, documents: list[Document]) -> int:
    """
    Dodaj dokumenty do indeksu.

    Args:
        documents: Lista dokumentów LlamaIndex

    Returns:
        Liczba zindeksowanych chunków

    Example:
        >>> from src.loaders import TextLoader
        >>> loader = TextLoader()
        >>> docs = loader.load(Path("./data/notes/"))
        >>> count = vector_store.add_documents(docs)
        >>> print(f"Zindeksowano {count} fragmentów")
    """
```

#### search()

```python
def search(
    self,
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[dict]:
    """
    Wyszukaj dokumenty przez podobieństwo.

    Args:
        query: Zapytanie tekstowe
        top_k: Liczba wyników
        filters: Filtry metadanych (opcjonalne)

    Returns:
        Lista dokumentów z metadanymi i score

    Example:
        >>> results = vs.search("projekt", filters={"source_type": "email"})
    """
```

#### search_with_priority()

```python
def search_with_priority(
    self,
    query: str,
    top_k: int = 10,
    fetch_k: int = 50,
    filters: dict | None = None,
) -> list[dict]:
    """
    Wyszukaj z ważeniem priorytetów (FR-P0-3).

    Pobiera więcej kandydatów (fetch_k) i re-rankuje
    z uwzględnieniem priorytetów dokumentów.

    Args:
        query: Zapytanie tekstowe
        top_k: Liczba zwracanych wyników
        fetch_k: Liczba kandydatów do re-rankingu
        filters: Filtry metadanych

    Returns:
        Lista dokumentów z:
            - similarity (float): Wynik podobieństwa
            - priority (float): Wynik priorytetu
            - final_score (float): Ważony wynik końcowy
    """
```

#### delete_document()

```python
def delete_document(self, document_id: str) -> bool:
    """
    Usuń dokument po ID (FR-P0-5).

    Args:
        document_id: UUID dokumentu

    Returns:
        True jeśli usunięto, False jeśli nie znaleziono

    Example:
        >>> success = vs.delete_document("550e8400-e29b-41d4-...")
    """
```

#### delete_by_filter()

```python
def delete_by_filter(self, filters: dict) -> int:
    """
    Usuń dokumenty pasujące do filtru.

    Args:
        filters: Filtry metadanych
            - source_type: Typ źródła
            - sender: Nadawca
            - date_before: Data (str ISO)

    Returns:
        Liczba usuniętych dokumentów

    Example:
        >>> count = vs.delete_by_filter({"sender": "spam@example.com"})
    """
```

#### update_metadata()

```python
def update_metadata(self, document_id: str, updates: dict) -> bool:
    """
    Aktualizuj metadane dokumentu.

    Args:
        document_id: UUID dokumentu
        updates: Słownik z aktualizacjami

    Returns:
        True jeśli zaktualizowano

    Example:
        >>> vs.update_metadata(doc_id, {"is_pinned": True})
    """
```

---

## ForgetService

Serwis usuwania danych (FR-P0-5, RTBF).

**Lokalizacja:** `src/rag/forget.py`

### Konstruktor

```python
class ForgetService:
    def __init__(
        self,
        vector_store: VectorStore,
        chat_history: ChatHistory,
        document_registry: DocumentRegistry,
        audit_logger: AuditLogger | None = None,
    ):
        """
        Inicjalizacja serwisu usuwania.

        Args:
            vector_store: Instancja VectorStore
            chat_history: Instancja ChatHistory
            document_registry: Instancja DocumentRegistry
            audit_logger: Instancja AuditLogger (opcjonalne)
        """
```

### Metody

#### forget_document()

```python
def forget_document(
    self,
    document_id: str,
    reason: str = "User request",
) -> ForgetResult:
    """
    Usuń pojedynczy dokument ze wszystkich systemów.

    Operacja:
    1. Usuwa wektory z Qdrant
    2. Usuwa referencje z ChatHistory
    3. Oznacza jako usunięty w Registry
    4. Loguje do Audit

    Args:
        document_id: UUID dokumentu
        reason: Powód usunięcia (do audytu)

    Returns:
        ForgetResult z podsumowaniem operacji

    Example:
        >>> result = forget.forget_document(doc_id, "RODO request")
        >>> print(f"Usunięto: {result.total_deleted}")
    """
```

#### forget_sender()

```python
def forget_sender(
    self,
    sender: str,
    reason: str = "GDPR request",
) -> ForgetResult:
    """
    Usuń wszystkie dokumenty od nadawcy.

    Args:
        sender: Email lub identyfikator nadawcy
        reason: Powód usunięcia

    Returns:
        ForgetResult

    Example:
        >>> result = forget.forget_sender("jan@example.com", "RODO Art. 17")
    """
```

#### forget_by_source_type()

```python
def forget_by_source_type(
    self,
    source_type: str,
    reason: str = "Bulk deletion",
) -> ForgetResult:
    """
    Usuń wszystkie dokumenty danego typu.

    Args:
        source_type: "email", "note", "whatsapp", "messenger"
        reason: Powód usunięcia

    Returns:
        ForgetResult

    Example:
        >>> result = forget.forget_by_source_type("whatsapp", "Privacy cleanup")
    """
```

### ForgetResult

```python
@dataclass
class ForgetResult:
    success: bool              # Czy operacja się powiodła
    vectors_deleted: int       # Usunięte wektory z Qdrant
    references_deleted: int    # Usunięte referencje z ChatHistory
    documents_deleted: int     # Zaktualizowane wpisy w Registry
    total_deleted: int         # Suma wszystkich
    timestamp: datetime        # Czas operacji
    reason: str                # Powód usunięcia
    audit_id: int | None       # ID wpisu w logu audytu
```

---

## ChatHistory

Zarządzanie historią konwersacji.

**Lokalizacja:** `src/storage/chat_history.py`

### Metody

```python
def create_conversation(self, title: str) -> int:
    """Utwórz nową konwersację."""

def get_conversations(self) -> list[Conversation]:
    """Pobierz listę konwersacji."""

def get_messages(self, conversation_id: int) -> list[Message]:
    """Pobierz wiadomości z konwersacji."""

def add_message(
    self,
    conversation_id: int,
    role: str,  # "user" | "assistant"
    content: str,
    sources: list[dict] | None = None,
) -> int:
    """Dodaj wiadomość do konwersacji."""

def get_recent_messages(
    self,
    conversation_id: int,
    limit: int = 10,
) -> list[Message]:
    """Pobierz ostatnie N wiadomości."""

def delete_conversation(self, conversation_id: int) -> bool:
    """Usuń konwersację."""

def purge_by_document(self, document_id: str) -> int:
    """Usuń referencje do dokumentu (FR-P0-5)."""

def purge_by_entity(
    self,
    entity_type: str,  # "sender", "source_type"
    entity_value: str,
) -> int:
    """Usuń referencje po encji."""
```

---

## DocumentRegistry

Śledzenie zindeksowanych dokumentów.

**Lokalizacja:** `src/storage/document_registry.py`

### Metody

```python
def register_document(
    self,
    file_path: str | Path,
    source_type: str,
    chunk_count: int,
    metadata: dict,
) -> TrackedDocument:
    """Zarejestruj nowy dokument."""

def get_by_id(self, document_id: str) -> TrackedDocument | None:
    """Pobierz dokument po ID."""

def get_by_path(self, file_path: str | Path) -> TrackedDocument | None:
    """Pobierz dokument po ścieżce."""

def mark_deleted(self, document_id: str) -> bool:
    """Oznacz dokument jako usunięty."""

def get_changed_files(self, directory: str | Path) -> dict[str, list[Path]]:
    """
    Wykryj zmienione pliki.

    Returns:
        dict:
            - "new": Nowe pliki
            - "modified": Zmienione pliki
            - "deleted": Usunięte pliki
    """

def get_all_active(self) -> list[TrackedDocument]:
    """Pobierz wszystkie aktywne dokumenty."""
```

### TrackedDocument

```python
@dataclass
class TrackedDocument:
    document_id: str
    file_path: str
    content_hash: str
    source_type: str
    chunk_count: int
    status: str  # "active", "deleted", "archived"
    indexed_at: datetime
    deleted_at: datetime | None
```

---

## AuditLogger

Logowanie operacji (privacy-safe).

**Lokalizacja:** `src/storage/audit.py`

### Metody

```python
def log(
    self,
    operation: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
) -> int | None:
    """
    Zaloguj operację.

    Args:
        operation: "index", "delete", "query", "export"
        entity_type: "document", "sender", "source_type"
        entity_id: ID lub wartość encji
        details: Dodatkowe szczegóły (bez treści!)

    Returns:
        ID wpisu lub None jeśli audit wyłączony
    """

def log_index(
    self,
    document_id: str,
    source_type: str,
    chunk_count: int,
) -> int | None:
    """Zaloguj indeksowanie dokumentu."""

def log_delete(
    self,
    document_id: str,
    reason: str,
    chunks_deleted: int,
) -> int | None:
    """Zaloguj usunięcie dokumentu."""

def get_entries(
    self,
    operation_type: str | None = None,
    entity_type: str | None = None,
    limit: int = 100,
) -> list[AuditEntry]:
    """Pobierz wpisy z logu."""
```

---

## LLM Factory

Tworzenie dostawców LLM.

**Lokalizacja:** `src/llm/factory.py`

### Funkcje

```python
def create_llm(provider: str | None = None) -> BaseLLM:
    """
    Utwórz dostawcę LLM.

    Args:
        provider: "gpt4all", "openai", "anthropic"
                  Domyślnie z config

    Returns:
        Instancja BaseLLM

    Raises:
        OfflineModeError: Jeśli cloud provider w trybie offline
        ValueError: Jeśli nieznany provider

    Example:
        >>> llm = create_llm("gpt4all")
        >>> llm = create_llm()  # z config
    """

def get_available_providers() -> list[str]:
    """
    Pobierz listę dostępnych providerów.

    Uwzględnia tryb offline i konfigurację.

    Returns:
        Lista nazw providerów

    Example:
        >>> providers = get_available_providers()
        >>> # W trybie offline: ["gpt4all"]
        >>> # Normalnie: ["gpt4all", "openai", "anthropic"]
    """

def is_offline_mode() -> bool:
    """Sprawdź czy system jest w trybie offline."""
```

### OfflineModeError

```python
class OfflineModeError(Exception):
    """Wyjątek dla prób użycia cloud LLM w trybie offline."""
    pass
```

---

## Priority System

System ważenia dokumentów (FR-P0-3).

**Lokalizacja:** `src/rag/priority.py`

### Typy

```python
class DocumentType(IntEnum):
    DECISION = 100     # Formalne decyzje
    NOTE = 70          # Notatki
    EMAIL = 50         # E-maile
    CONVERSATION = 30  # Czaty

class ApprovalStatus(IntEnum):
    PINNED = 50        # Przypięty
    APPROVED = 30      # Zatwierdzony
    AUTOMATIC = 0      # Automatyczny
```

### Funkcje

```python
def calculate_priority(
    source_type: str,
    date: str | datetime,
    is_pinned: bool = False,
    is_approved: bool = False,
) -> DocumentPriority:
    """
    Oblicz priorytet dokumentu.

    Args:
        source_type: "email", "note", "whatsapp", "messenger"
        date: Data dokumentu
        is_pinned: Czy przypięty
        is_approved: Czy zatwierdzony

    Returns:
        DocumentPriority z rozbiciem scoringu
    """

def rank_documents(
    documents: list[dict],
    similarity_weight: float = 0.7,
    priority_weight: float = 0.3,
) -> list[RankedDocument]:
    """
    Przerankuj dokumenty z wagami.

    Args:
        documents: Lista dokumentów z "similarity" i "priority"
        similarity_weight: Waga podobieństwa
        priority_weight: Waga priorytetu

    Returns:
        Posortowana lista RankedDocument
    """
```

### DocumentPriority

```python
@dataclass
class DocumentPriority:
    type_score: float        # 0.30-1.00
    recency_score: float     # 0.00-1.00
    approval_score: float    # 0.00-0.50
    priority_score: float    # Połączony wynik 0.00-1.00
```

---

## Citations

System cytatów (FR-P0-1).

**Lokalizacja:** `src/rag/citations.py`

### Typy

```python
@dataclass
class Citation:
    document_id: str
    source_type: str
    filename: str
    date: str
    fragment: str      # Do 100 znaków
    score: float

    def to_dict(self) -> dict:
        """Konwersja do słownika."""

@dataclass
class GroundedResponse:
    answer: str
    citations: list[Citation]
    is_grounded: bool
    no_context_found: bool
    conversation_id: int | None
    query_time_ms: float

    @property
    def sources(self) -> list[dict]:
        """Legacy format dla kompatybilności."""
```

### Funkcje

```python
def extract_citations(source_nodes: list) -> list[Citation]:
    """Wyciągnij cytaty z LlamaIndex NodeWithScore."""

def validate_grounding(answer: str, citations: list[Citation]) -> bool:
    """Sprawdź czy odpowiedź jest uziemiona."""

# Stała
GROUNDED_SYSTEM_PROMPT: str  # Prompt wymuszający cytaty
```

---

## Explainability

System wyjaśnień RAG (FR-P0-4).

**Lokalizacja:** `src/rag/explainability.py`

### Typy

```python
@dataclass
class RetrievalExplanation:
    document_id: str
    filename: str
    source_type: str
    similarity_score: float
    priority_score: float
    final_score: float
    type_contribution: float
    recency_contribution: float
    approval_contribution: float
    rank: int
    passed_filters: list[str]

@dataclass
class ContextFragment:
    text: str
    source_id: str
    source_type: str
    token_count: int
    truncated: bool

@dataclass
class ContextWindowExplanation:
    total_tokens: int
    max_tokens: int
    utilization: float
    fragments: list[ContextFragment]
    fragment_count: int
    overflow_documents: int
    overflow_tokens: int

@dataclass
class RAGExplanation:
    query_text: str
    query_embedding_model: str
    retrieval_mode: str
    retrieval_top_k: int
    documents_retrieved: list[RetrievalExplanation]
    context_window: ContextWindowExplanation | None
    response_mode: str
    llm_provider: str
    llm_model: str
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    filters_applied: dict
    timestamp: datetime
```

### Funkcje

```python
def create_retrieval_explanation(
    node,
    rank: int,
    priority_info: dict | None = None,
) -> RetrievalExplanation:
    """Utwórz wyjaśnienie dla dokumentu."""

def create_context_explanation(
    source_nodes: list,
    max_tokens: int = 4000,
) -> ContextWindowExplanation:
    """Utwórz wyjaśnienie kontekstu."""

def format_explanation_summary(
    explanation: RAGExplanation
) -> str:
    """Sformatuj wyjaśnienie jako tekst."""

def estimate_tokens(text: str) -> int:
    """Oszacuj liczbę tokenów (4 chars = 1 token)."""
```

---

<p align="center">
  <a href="Integracje">← Integracje</a> |
  <a href="Home">Strona główna</a> |
  <a href="FAQ">FAQ →</a>
</p>
