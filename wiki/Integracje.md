# Integracje i rozszerzenia

Jak rozszerzyć Digital Twin o dodatkowe źródła danych, API i automatyzacje.

---

## Spis treści

1. [Obecne integracje](#obecne-integracje)
2. [Planowane integracje](#planowane-integracje)
3. [Własne loadery](#własne-loadery)
4. [REST API (koncepcja)](#rest-api-koncepcja)
5. [Webhooks i automatyzacja](#webhooks-i-automatyzacja)
6. [Integracje z narzędziami](#integracje-z-narzędziami)

---

## Obecne integracje

### Obsługiwane formaty danych

| Źródło | Loader | Formaty | Status |
|--------|--------|---------|:------:|
| Notatki | `TextLoader` | .txt, .md | ✅ |
| E-mail | `EmailLoader` | .eml, .mbox | ✅ |
| WhatsApp | `WhatsAppLoader` | .txt (eksport) | ✅ |
| Messenger | `MessengerLoader` | .json (FB export) | ✅ |

### Baza wektorowa

| System | Status | Uwagi |
|--------|:------:|-------|
| Qdrant | ✅ | Domyślny, Docker |
| Qdrant Cloud | ✅ | Zmień QDRANT_HOST |

### Modele LLM

| Provider | Status | Uwagi |
|----------|:------:|-------|
| GPT4All | ✅ | Lokalny, offline |
| OpenAI | ✅ | API, wymaga klucza |
| Anthropic | ✅ | API, wymaga klucza |

### Embeddingi

| Model | Status | Uwagi |
|-------|:------:|-------|
| all-MiniLM-L6-v2 | ✅ | Domyślny, EN |
| paraphrase-multilingual | ✅ | Wielojęzyczny |
| all-mpnet-base-v2 | ✅ | Większy, dokładniejszy |

---

## Planowane integracje

### P1 — Very Important

| Integracja | Opis | Priorytet |
|------------|------|:---------:|
| PDF | Dokumenty PDF | P1 |
| DOCX | Dokumenty Word | P1 |
| Obsidian | Vault sync | P1 |
| Notion | API export | P2 |

### P2 — Important

| Integracja | Opis | Priorytet |
|------------|------|:---------:|
| Google Calendar | Wydarzenia | P2 |
| Outlook | E-mail + kalendarz | P2 |
| Slack | Wiadomości | P2 |
| Discord | Wiadomości | P2 |
| Telegram | Eksport | P2 |

### P3 — Nice to have

| Integracja | Opis | Priorytet |
|------------|------|:---------:|
| Evernote | Notatki | P3 |
| Apple Notes | Notatki | P3 |
| iMessage | Wiadomości | P3 |
| Signal | Eksport | P3 |

---

## Własne loadery

Możesz stworzyć własny loader dla dowolnego formatu danych.

### Szablon loadera

```python
# src/loaders/my_custom_loader.py

from pathlib import Path
from typing import Iterator
from src.loaders.base import BaseLoader

class MyCustomLoader(BaseLoader):
    """Loader dla mojego formatu."""

    source_type = "my_format"
    supported_extensions = [".myext", ".custom"]

    def _find_files(self, directory: Path) -> Iterator[Path]:
        """Znajdź pliki do przetworzenia."""
        for ext in self.supported_extensions:
            yield from directory.rglob(f"*{ext}")

    def _parse_file(self, file_path: Path) -> str:
        """Parsuj plik i zwróć treść tekstową."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Twoje parsowanie...
        parsed_content = self._custom_parse(content)

        return parsed_content

    def _extract_metadata(self, file_path: Path, content: str) -> dict:
        """Wyciągnij metadane z pliku."""
        base_metadata = super()._extract_metadata(file_path, content)

        # Dodaj własne metadane
        base_metadata.update({
            "custom_field": self._extract_custom_field(content),
            "another_field": "value",
        })

        return base_metadata

    def _custom_parse(self, content: str) -> str:
        """Własna logika parsowania."""
        # Implementacja...
        return content
```

### Rejestracja loadera

```python
# src/loaders/__init__.py

from .my_custom_loader import MyCustomLoader

__all__ = [
    # ... istniejące
    "MyCustomLoader",
]
```

### Użycie loadera

```python
from src.loaders import MyCustomLoader

loader = MyCustomLoader()
documents = loader.load(Path("./data/my_format/"))
```

---

### Przykład: PDF Loader (koncepcja)

```python
# src/loaders/pdf_loader.py

from pathlib import Path
from typing import Iterator
from src.loaders.base import BaseLoader

# Wymaga: pip install pypdf2 lub pdfplumber

class PDFLoader(BaseLoader):
    """Loader dla dokumentów PDF."""

    source_type = "pdf"
    supported_extensions = [".pdf"]

    def __init__(self):
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
        except ImportError:
            raise ImportError("Install pdfplumber: pip install pdfplumber")

    def _parse_file(self, file_path: Path) -> str:
        """Wyciągnij tekst z PDF."""
        text_parts = []

        with self.pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    def _extract_metadata(self, file_path: Path, content: str) -> dict:
        """Wyciągnij metadane z PDF."""
        base_metadata = super()._extract_metadata(file_path, content)

        with self.pdfplumber.open(file_path) as pdf:
            info = pdf.metadata or {}
            base_metadata.update({
                "pdf_title": info.get("Title", ""),
                "pdf_author": info.get("Author", ""),
                "pdf_pages": len(pdf.pages),
            })

        return base_metadata
```

---

### Przykład: Obsidian Loader (koncepcja)

```python
# src/loaders/obsidian_loader.py

import re
from pathlib import Path
from src.loaders.base import BaseLoader

class ObsidianLoader(BaseLoader):
    """Loader dla Obsidian vault."""

    source_type = "obsidian"
    supported_extensions = [".md"]

    def _parse_file(self, file_path: Path) -> str:
        """Parsuj notatkę Obsidian."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Usuń Obsidian-specific syntax
        content = self._remove_obsidian_links(content)
        content = self._process_callouts(content)

        return content

    def _remove_obsidian_links(self, content: str) -> str:
        """Zamień [[links]] na zwykły tekst."""
        # [[note]] → note
        content = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', content)
        return content

    def _process_callouts(self, content: str) -> str:
        """Przetwórz callout'y Obsidian."""
        # > [!note] Title → Note: Title
        content = re.sub(
            r'> \[!(\w+)\]\s*(.*)',
            r'[\1] \2',
            content
        )
        return content

    def _extract_metadata(self, file_path: Path, content: str) -> dict:
        """Wyciągnij metadane + YAML frontmatter."""
        base_metadata = super()._extract_metadata(file_path, content)

        # Parse YAML frontmatter
        frontmatter = self._parse_frontmatter(content)
        if frontmatter:
            base_metadata.update({
                "tags": frontmatter.get("tags", []),
                "aliases": frontmatter.get("aliases", []),
                "obsidian_type": frontmatter.get("type", "note"),
            })

            # Wykryj typ dokumentu z frontmatter
            if frontmatter.get("type") == "decision":
                base_metadata["document_category"] = "decision"

        return base_metadata

    def _parse_frontmatter(self, content: str) -> dict:
        """Parsuj YAML frontmatter."""
        import yaml

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1])
                except yaml.YAMLError:
                    pass
        return {}
```

---

## REST API (koncepcja)

Planowane REST API dla integracji z innymi aplikacjami.

### Endpoint'y

```
POST /api/query          - Zadaj pytanie
POST /api/search         - Wyszukaj dokumenty
POST /api/index          - Zindeksuj dokument
DELETE /api/documents    - Usuń dokumenty
GET /api/stats           - Statystyki systemu
GET /api/conversations   - Lista konwersacji
```

### Przykładowa implementacja (FastAPI)

```python
# src/api/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.rag import RAGEngine
from src.rag import ForgetService

app = FastAPI(title="Digital Twin API")
engine = RAGEngine()

class QueryRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    include_explanation: bool = False

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    is_grounded: bool
    query_time_ms: float

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Zadaj pytanie do systemu RAG."""
    result = engine.query(
        question=request.question,
        conversation_id=request.conversation_id,
        include_explanation=request.include_explanation,
    )
    return QueryResponse(**result)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    source_type: str | None = None

@app.post("/api/search")
async def search(request: SearchRequest):
    """Wyszukaj dokumenty."""
    results = engine.search(
        query=request.query,
        top_k=request.top_k,
        source_type=request.source_type,
    )
    return {"results": results, "count": len(results)}

class ForgetRequest(BaseModel):
    document_id: str | None = None
    sender: str | None = None
    reason: str = "API request"

@app.delete("/api/documents")
async def forget(request: ForgetRequest):
    """Usuń dokumenty z systemu."""
    forget_service = ForgetService(...)

    if request.document_id:
        result = forget_service.forget_document(
            request.document_id, request.reason
        )
    elif request.sender:
        result = forget_service.forget_sender(
            request.sender, request.reason
        )
    else:
        raise HTTPException(400, "Specify document_id or sender")

    return {
        "success": result.success,
        "deleted_count": result.total_deleted,
    }

@app.get("/api/stats")
async def stats():
    """Pobierz statystyki systemu."""
    return engine.get_stats()
```

### Uruchomienie API

```bash
# Instalacja
pip install fastapi uvicorn

# Uruchomienie
uvicorn src.api.main:app --reload --port 8000

# Dokumentacja
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

---

## Webhooks i automatyzacja

### Koncepcja webhooków

```python
# src/hooks/webhooks.py

import httpx
from dataclasses import dataclass
from typing import Callable

@dataclass
class WebhookConfig:
    url: str
    events: list[str]  # ["document.indexed", "document.deleted", "query"]
    secret: str | None = None

class WebhookManager:
    def __init__(self):
        self.webhooks: list[WebhookConfig] = []

    def register(self, config: WebhookConfig):
        """Zarejestruj webhook."""
        self.webhooks.append(config)

    async def emit(self, event: str, data: dict):
        """Wyślij event do wszystkich webhooków."""
        for webhook in self.webhooks:
            if event in webhook.events:
                await self._send(webhook, event, data)

    async def _send(self, webhook: WebhookConfig, event: str, data: dict):
        """Wyślij request do webhooka."""
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        headers = {}
        if webhook.secret:
            headers["X-Webhook-Secret"] = webhook.secret

        async with httpx.AsyncClient() as client:
            await client.post(webhook.url, json=payload, headers=headers)
```

### Przykładowe eventy

```python
# Po zindeksowaniu dokumentu
await webhook_manager.emit("document.indexed", {
    "document_id": doc.id,
    "source_type": doc.source_type,
    "filename": doc.filename,
})

# Po usunięciu
await webhook_manager.emit("document.deleted", {
    "document_id": doc_id,
    "reason": reason,
    "deleted_count": result.total_deleted,
})

# Po zapytaniu (opcjonalnie)
await webhook_manager.emit("query", {
    "question_length": len(question),  # Bez treści!
    "sources_count": len(result["sources"]),
    "query_time_ms": result["query_time_ms"],
})
```

---

## Integracje z narzędziami

### Obsidian (przez pliki)

```bash
# Symlink do vault'a
ln -s ~/Obsidian/MyVault data/obsidian

# Indeksuj
python scripts/ingest.py --source ./data/ --types obsidian
```

### Logseq (przez pliki)

```bash
# Symlink
ln -s ~/Logseq/journals data/logseq/journals
ln -s ~/Logseq/pages data/logseq/pages

# Indeksuj (użyj TextLoader)
python scripts/ingest.py --source ./data/logseq/
```

### Google Takeout

```bash
# 1. Pobierz Takeout z Google
# 2. Rozpakuj

# Gmail (MBOX)
cp ~/takeout/Mail/*.mbox data/emails/

# Keep (JSON → konwersja do TXT)
# Wymaga własnego loadera
```

### Apple Notes (eksport)

```bash
# 1. W Notes.app: File → Export as PDF lub TXT
# 2. Lub użyj narzędzia: https://github.com/threeplanetssoftware/apple_cloud_notes_parser

cp ~/exports/notes/*.txt data/notes/
```

### Notion (export)

```bash
# 1. W Notion: Settings → Export → Markdown & CSV
# 2. Rozpakuj

cp ~/exports/notion/**/*.md data/notes/notion/
```

---

## Integracja z kalendarzem (koncepcja)

```python
# src/loaders/calendar_loader.py

from icalendar import Calendar
from pathlib import Path
from src.loaders.base import BaseLoader

class CalendarLoader(BaseLoader):
    """Loader dla plików iCal (.ics)."""

    source_type = "calendar"
    supported_extensions = [".ics"]

    def _parse_file(self, file_path: Path) -> str:
        """Wyciągnij wydarzenia z kalendarza."""
        with open(file_path, "rb") as f:
            cal = Calendar.from_ical(f.read())

        events = []
        for component in cal.walk():
            if component.name == "VEVENT":
                event_text = self._format_event(component)
                events.append(event_text)

        return "\n\n---\n\n".join(events)

    def _format_event(self, event) -> str:
        """Formatuj wydarzenie jako tekst."""
        return f"""
Event: {event.get('SUMMARY', 'No title')}
Date: {event.get('DTSTART').dt}
Location: {event.get('LOCATION', 'N/A')}
Description: {event.get('DESCRIPTION', 'No description')}
Attendees: {', '.join(str(a) for a in event.get('ATTENDEE', []))}
"""
```

---

## Tips

### Bezpieczeństwo integracji

```python
# Zawsze używaj offline mode dla wrażliwych danych
OFFLINE_MODE=true

# Nie indeksuj haseł i tokenów
# Sprawdzaj pliki przed indeksowaniem
```

### Wydajność

```python
# Dla dużych wolumenów — indeksuj batch'ami
for batch in chunks(documents, size=100):
    vector_store.add_documents(batch)

# Monitoruj użycie pamięci
import psutil
print(f"RAM: {psutil.Process().memory_info().rss / 1024**2:.0f} MB")
```

---

<p align="center">
  <a href="Scenariusze-użycia">← Scenariusze użycia</a> |
  <a href="Home">Strona główna</a> |
  <a href="API-Reference">API Reference →</a>
</p>
