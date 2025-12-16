# FR-P0-4: Explainability

**Status:** ✅ Zaimplementowane (v1.0)

Pełna transparentność systemu RAG — **widzisz dokładnie** które fragmenty weszły do kontekstu i **dlaczego**.

---

## Problem

Systemy RAG są często "czarną skrzynką":

```
Pytanie: "Kiedy jest deadline projektu?"

❓ Odpowiedź: "Deadline to 31 marca 2025"

Ale skąd to wiem?
- Które dokumenty zostały użyte?
- Dlaczego właśnie te?
- Ile było kandydatów?
- Jak działał scoring?
```

**Bez wyjaśnień:** brak zaufania do odpowiedzi, trudność w debugowaniu.

---

## Rozwiązanie

Digital Twin oferuje **kompletne wyjaśnienie** każdego zapytania:

```python
result = engine.query(
    "Kiedy jest deadline projektu?",
    include_explanation=True
)

explanation = result["explanation"]
# Zawiera: dokumenty, scoring, timing, kontekst...
```

---

## Struktura wyjaśnienia

### RAGExplanation (główna struktura)

```python
@dataclass
class RAGExplanation:
    # Zapytanie
    query_text: str                    # Tekst zapytania
    query_embedding_model: str         # Model embeddingów

    # Retrieval
    retrieval_mode: str                # "similarity" lub "priority_weighted"
    retrieval_top_k: int               # Ile dokumentów pobrano
    documents_retrieved: list[RetrievalExplanation]

    # Kontekst
    context_window: ContextWindowExplanation

    # Generowanie
    response_mode: str                 # "compact", "refine", etc.
    llm_provider: str                  # "gpt4all", "openai", etc.
    llm_model: str                     # Nazwa modelu

    # Timing (milisekundy)
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float

    # Filtry
    filters_applied: dict              # Aktywne filtry
    timestamp: datetime                # Czas zapytania
```

### RetrievalExplanation (per dokument)

```python
@dataclass
class RetrievalExplanation:
    # Identyfikacja
    document_id: str
    filename: str
    source_type: str

    # Scoring
    similarity_score: float      # Podobieństwo wektorowe (0-1)
    priority_score: float        # Priorytet dokumentu (0-1)
    final_score: float           # Ważony wynik końcowy (0-1)

    # Rozbicie priorytetu
    type_contribution: float     # Wkład z typu dokumentu
    recency_contribution: float  # Wkład z aktualności
    approval_contribution: float # Wkład ze statusu zatwierdzenia

    # Pozycja
    rank: int                    # Miejsce w rankingu
    passed_filters: list[str]   # Które filtry przeszedł
```

### ContextWindowExplanation (kontekst LLM)

```python
@dataclass
class ContextWindowExplanation:
    # Tokeny
    total_tokens: int            # Użyte tokeny
    max_tokens: int              # Maksimum dozwolone
    utilization: float           # Procent wykorzystania

    # Fragmenty
    fragments: list[ContextFragment]
    fragment_count: int

    # Overflow
    overflow_documents: int      # Dokumenty pominięte (brak miejsca)
    overflow_tokens: int         # Tokeny pominięte
```

---

## Użycie w kodzie

### Podstawowe wyjaśnienie

```python
from src.rag import RAGEngine

engine = RAGEngine()

result = engine.query(
    "Jakie zadania mam na ten tydzień?",
    include_explanation=True
)

exp = result["explanation"]

# Podsumowanie
print(f"⏱️ Czas: {exp['timing']['total_ms']:.0f}ms")
print(f"  - Retrieval: {exp['timing']['retrieval_ms']:.0f}ms")
print(f"  - Generation: {exp['timing']['generation_ms']:.0f}ms")
```

### Analiza pobranych dokumentów

```python
print(f"\n📚 Dokumenty ({len(exp['documents_retrieved'])}):")

for doc in exp["documents_retrieved"]:
    print(f"\n  {doc['rank']}. {doc['filename']}")
    print(f"     Typ: {doc['source_type']}")
    print(f"     Similarity: {doc['similarity_score']:.3f}")
    print(f"     Priority: {doc['priority_score']:.3f}")
    print(f"     Final: {doc['final_score']:.3f}")

    # Rozbicie priorytetu
    print(f"     Składniki:")
    print(f"       - Type: {doc['type_contribution']:.2f}")
    print(f"       - Recency: {doc['recency_contribution']:.2f}")
    print(f"       - Approval: {doc['approval_contribution']:.2f}")
```

### Analiza kontekstu

```python
ctx = exp["context_window"]

print(f"\n📝 Kontekst LLM:")
print(f"   Tokeny: {ctx['total_tokens']}/{ctx['max_tokens']} ({ctx['utilization']:.0%})")
print(f"   Fragmentów: {ctx['fragment_count']}")

if ctx["overflow_documents"] > 0:
    print(f"   ⚠️ Pominięto {ctx['overflow_documents']} dokumentów (brak miejsca)")

print(f"\n   Fragmenty:")
for frag in ctx["fragments"]:
    print(f"   - [{frag['source_type']}] {frag['source_id']}")
    print(f"     {frag['text'][:60]}...")
    print(f"     ({frag['token_count']} tokenów)")
```

### Pełny przykład

```python
def explain_query(question: str):
    """Wykonaj zapytanie i wyświetl pełne wyjaśnienie."""
    engine = RAGEngine()
    result = engine.query(question, include_explanation=True)

    print(f"❓ Pytanie: {question}\n")
    print(f"💬 Odpowiedź: {result['answer']}\n")
    print("=" * 60)

    exp = result["explanation"]

    # Timing
    print(f"\n⏱️ TIMING")
    print(f"   Total: {exp['timing']['total_ms']:.0f}ms")
    print(f"   Retrieval: {exp['timing']['retrieval_ms']:.0f}ms")
    print(f"   Generation: {exp['timing']['generation_ms']:.0f}ms")

    # Retrieval
    print(f"\n🔍 RETRIEVAL")
    print(f"   Mode: {exp['retrieval_mode']}")
    print(f"   Top-K: {exp['retrieval_top_k']}")
    print(f"   Embedding: {exp['query_embedding_model']}")

    # Dokumenty
    print(f"\n📚 DOKUMENTY POBRANE ({len(exp['documents_retrieved'])})")
    for doc in exp["documents_retrieved"]:
        print(f"\n   [{doc['rank']}] {doc['filename']}")
        print(f"       sim={doc['similarity_score']:.2f} "
              f"pri={doc['priority_score']:.2f} "
              f"→ {doc['final_score']:.2f}")

    # Kontekst
    ctx = exp["context_window"]
    print(f"\n📝 KONTEKST")
    print(f"   Tokens: {ctx['total_tokens']}/{ctx['max_tokens']} ({ctx['utilization']:.0%})")
    print(f"   Fragments: {ctx['fragment_count']}")

    # LLM
    print(f"\n🤖 LLM")
    print(f"   Provider: {exp['llm_provider']}")
    print(f"   Model: {exp['llm_model']}")
    print(f"   Mode: {exp['response_mode']}")

# Użycie
explain_query("Kiedy jest deadline projektu Alpha?")
```

---

## Przykładowy output

```
❓ Pytanie: Kiedy jest deadline projektu Alpha?

💬 Odpowiedź: Deadline projektu Alpha to 31 marca 2025, zgodnie z
ostatnimi ustaleniami z zespołem.
[Źródło: email, 2024-12-10, "Deadline Alpha: 31.03.2025"]

============================================================

⏱️ TIMING
   Total: 1247ms
   Retrieval: 89ms
   Generation: 1158ms

🔍 RETRIEVAL
   Mode: priority_weighted
   Top-K: 5
   Embedding: sentence-transformers/all-MiniLM-L6-v2

📚 DOKUMENTY POBRANE (5)

   [1] email_2024-12-10_deadline.eml
       sim=0.89 pri=0.72 → 0.84

   [2] notes/projekt-alpha.md
       sim=0.85 pri=0.65 → 0.79

   [3] whatsapp_team_alpha.txt
       sim=0.91 pri=0.35 → 0.74

   [4] email_2024-11-15_planning.eml
       sim=0.78 pri=0.58 → 0.72

   [5] notes/spotkanie-2024-11.md
       sim=0.75 pri=0.55 → 0.69

📝 KONTEKST
   Tokens: 1847/4000 (46%)
   Fragments: 5

🤖 LLM
   Provider: gpt4all
   Model: mistral-7b-instruct-v0.1.Q4_0.gguf
   Mode: compact
```

---

## Formatowanie dla użytkownika

### Czytelne podsumowanie

```python
from src.rag.explainability import format_explanation_summary

result = engine.query("...", include_explanation=True)

# Sformatowane podsumowanie
summary = format_explanation_summary(result["explanation"])
print(summary)
```

**Output:**
```
Query processed in 1247ms
  Retrieval: 89ms (priority_weighted)
  Generation: 1158ms (gpt4all)

Documents retrieved: 5
  Top sources:
    1. email_2024-12-10_deadline.eml (sim: 0.89, pri: 0.72)
    2. notes/projekt-alpha.md (sim: 0.85, pri: 0.65)
    3. whatsapp_team_alpha.txt (sim: 0.91, pri: 0.35)

Context: 1847/4000 tokens (46% used)
```

---

## UI — wyświetlanie wyjaśnień

W Streamlit można stworzyć zakładki:

```python
import streamlit as st

def render_explanation(explanation: dict):
    """Renderuj wyjaśnienie w Streamlit."""

    tabs = st.tabs(["📚 Dokumenty", "📝 Kontekst", "⏱️ Timing", "🔧 Szczegóły"])

    with tabs[0]:  # Dokumenty
        for doc in explanation["documents_retrieved"]:
            with st.expander(f"{doc['rank']}. {doc['filename']}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Similarity", f"{doc['similarity_score']:.2f}")
                col2.metric("Priority", f"{doc['priority_score']:.2f}")
                col3.metric("Final", f"{doc['final_score']:.2f}")

                st.write(f"**Typ:** {doc['source_type']}")

    with tabs[1]:  # Kontekst
        ctx = explanation["context_window"]
        st.progress(ctx["utilization"])
        st.write(f"**Tokeny:** {ctx['total_tokens']}/{ctx['max_tokens']}")
        st.write(f"**Fragmentów:** {ctx['fragment_count']}")

    with tabs[2]:  # Timing
        timing = explanation["timing"]
        st.metric("Total", f"{timing['total_ms']:.0f}ms")
        st.metric("Retrieval", f"{timing['retrieval_ms']:.0f}ms")
        st.metric("Generation", f"{timing['generation_ms']:.0f}ms")

    with tabs[3]:  # Szczegóły
        st.json(explanation)
```

---

## Debugging z wyjaśnieniami

### Dlaczego nie znaleziono dokumentu?

```python
# Sprawdź parametry retrievalu
print(f"Top-K: {exp['retrieval_top_k']}")
print(f"Mode: {exp['retrieval_mode']}")

# Sprawdź scoring pierwszego dokumentu
top_doc = exp["documents_retrieved"][0]
print(f"Najlepszy similarity: {top_doc['similarity_score']}")
# Jeśli niski (<0.5) — zapytanie nie pasuje semantycznie

# Sprawdź czy priorytet nie zdominował
print(f"Priority weight: {settings.priority_document_weight}")
```

### Dlaczego odpowiedź jest wolna?

```python
timing = exp["timing"]

if timing["retrieval_ms"] > 500:
    print("⚠️ Wolny retrieval — sprawdź indeks Qdrant")

if timing["generation_ms"] > 5000:
    print("⚠️ Wolna generacja — rozważ mniejszy model lub TOP_K")
```

### Dlaczego kontekst jest przeładowany?

```python
ctx = exp["context_window"]

if ctx["utilization"] > 0.9:
    print("⚠️ Kontekst prawie pełny")
    print(f"   Overflow: {ctx['overflow_documents']} dokumentów")
    print("   Rozwiązanie: zmniejsz TOP_K lub CHUNK_SIZE")
```

---

## Konfiguracja

### Włączanie wyjaśnień

```python
# Per-zapytanie
result = engine.query("...", include_explanation=True)

# Domyślnie wyłączone (oszczędność tokenów)
result = engine.query("...")  # Bez explanation
```

### Maksymalna ilość kontekstu

```bash
# .env — dla kontekstu LLM
CHUNK_SIZE=512
TOP_K=5
```

---

## Powiązane

- **[FR-P0-3: Priority Rules](FR-P0-3-Priority-Rules)** — jak działa scoring
- **[FR-P0-1: Grounded Answers](FR-P0-1-Grounded-Answers)** — cytaty w odpowiedziach
- **[Pipelines](Pipelines)** — przepływ danych przez RAG

---

<p align="center">
  <a href="FR-P0-3-Priority-Rules">← FR-P0-3: Priority Rules</a> |
  <a href="Home">Strona główna</a> |
  <a href="FR-P0-5-Forget-RTBF">FR-P0-5: Forget/RTBF →</a>
</p>
