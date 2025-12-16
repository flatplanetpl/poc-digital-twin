# FR-P0-1: Grounded Answers

**Status:** ✅ Zaimplementowane (v1.0)

Grounded Answers to fundament zaufania do systemu — odpowiedzi **wyłącznie** na podstawie Twoich dokumentów z **obowiązkowymi cytatami**.

---

## Problem

Tradycyjne modele językowe (LLM) mają tendencję do "halucynacji" — generowania odpowiedzi, które brzmią przekonująco, ale są całkowicie zmyślone. To szczególnie niebezpieczne gdy:

- Pytasz o **fakty z własnych dokumentów** (daty, kwoty, ustalenia)
- Podejmujesz **decyzje biznesowe** na podstawie odpowiedzi
- Sprawdzasz **historię komunikacji** (kto co powiedział)

**Przykład halucynacji:**

```
Pytanie: Kiedy umówiłem się z Anną?

❌ Typowe LLM: "Umówiłeś się z Anną na piątek o 14:00."
   (skąd to wie? wymyśliło!)

✅ Digital Twin: "Nie mogłem znaleźć informacji o spotkaniu z Anną
   w Twoich dokumentach."
   (uczciwe — jeśli nie ma danych, mówi że nie wie)
```

---

## Rozwiązanie

Digital Twin używa specjalnego **Grounded System Prompt**, który wymusza:

1. **TYLKO kontekst** — LLM może używać wyłącznie dostarczonych fragmentów
2. **Obowiązkowe cytaty** — każdy fakt musi mieć źródło
3. **Przyznanie się do niewiedzy** — jeśli nie ma danych, mówi wprost

### Grounded System Prompt

```
Jesteś osobistym asystentem danych. Odpowiadaj TYLKO na podstawie kontekstu.

KRYTYCZNE ZASADY:
1. Używaj WYŁĄCZNIE informacji jawnie zawartych w kontekście poniżej
2. Jeśli informacji nie ma: "Nie mogłem znaleźć tej informacji w Twoich danych."
3. NIGDY nie używaj wiedzy z treningu modelu
4. ZAWSZE cytuj źródło: [Źródło: {typ}, {data}, "{fragment}"]

Kontekst:
{context_str}

Pytanie: {query_str}
```

---

## Struktura cytatu

Każdy cytat zawiera pełne metadane źródła:

```python
@dataclass
class Citation:
    document_id: str      # UUID dokumentu (do śledzenia/usuwania)
    source_type: str      # email, note, whatsapp, messenger
    filename: str         # Nazwa pliku źródłowego
    date: str             # Data dokumentu
    fragment: str         # Cytowany fragment (do 100 znaków)
    score: float          # Wynik podobieństwa (0.0 - 1.0)
```

### Przykład cytatu w odpowiedzi

```
Zgodnie z Twoimi dokumentami, spotkanie zostało przełożone na poniedziałek.

[Źródło: email, 2024-12-10, "Musimy przełożyć spotkanie na poniedziałek..."]
[Źródło: whatsapp, 2024-12-10, "Ok, to w poniedziałek o 10"]
```

---

## Użycie w kodzie

### Podstawowe zapytanie z cytatami

```python
from src.rag import RAGEngine

engine = RAGEngine()

result = engine.query("Kiedy mam spotkanie z klientem?")

# Odpowiedź
print(result["answer"])

# Cytaty
for citation in result["citations"]:
    print(f"📎 [{citation['source_type']}] {citation['filename']}")
    print(f"   Data: {citation['date']}")
    print(f"   Fragment: {citation['fragment']}")
    print(f"   Score: {citation['score']:.2f}")
```

### Sprawdzanie uziemienia

```python
result = engine.query("Co obiecałem Markowi?")

if result["is_grounded"]:
    print("✅ Odpowiedź oparta na dokumentach")
else:
    print("⚠️ UWAGA: Odpowiedź może zawierać treści spoza kontekstu")

if result["no_context_found"]:
    print("❌ Nie znaleziono pasujących dokumentów")
```

### GroundedResponse — pełna struktura

```python
from src.rag.citations import GroundedResponse

# GroundedResponse zawiera:
@dataclass
class GroundedResponse:
    answer: str                    # Treść odpowiedzi
    citations: list[Citation]      # Lista cytatów
    is_grounded: bool              # Czy odpowiedź jest uziemiona
    no_context_found: bool         # Czy nie znaleziono kontekstu
    conversation_id: int | None    # ID konwersacji
    query_time_ms: float           # Czas zapytania

    @property
    def sources(self) -> list[dict]:
        """Legacy format dla kompatybilności."""
        return [c.to_dict() for c in self.citations]
```

---

## Walidacja uziemienia

System automatycznie sprawdza czy odpowiedź jest prawidłowo uziemiona:

```python
from src.rag.citations import validate_grounding

# Funkcja sprawdza:
# 1. Czy odpowiedź zawiera cytaty
# 2. Czy cytaty odpowiadają faktycznie pobranym dokumentom
# 3. Czy odpowiedź nie zawiera "halucynacji"

is_grounded = validate_grounding(answer_text, citations)
```

### Heurystyki walidacji

| Warunek | Wynik |
|---------|-------|
| Odpowiedź zawiera `[Źródło: ...]` | +1 do grounding |
| Cytaty pasują do pobranych dokumentów | +1 do grounding |
| Odpowiedź mówi "nie znaleziono" przy braku kontekstu | ✅ Grounded |
| Odpowiedź podaje fakty bez cytatów | ❌ Not grounded |

---

## Ekstrakcja cytatów

System automatycznie wyciąga cytaty z odpowiedzi LLM:

```python
from src.rag.citations import extract_citations

# Z listy NodeWithScore (LlamaIndex)
citations = extract_citations(response.source_nodes)

for c in citations:
    print(f"{c.source_type}: {c.fragment[:50]}... (score: {c.score:.2f})")
```

---

## Konfiguracja

### Prompt systemowy

Możesz dostosować prompt w `src/rag/query_engine.py`:

```python
class RAGEngine:
    SYSTEM_PROMPT = GROUNDED_SYSTEM_PROMPT  # Z citations.py
```

### Lub użyć własnego:

```python
from src.rag.citations import GROUNDED_SYSTEM_PROMPT

custom_prompt = GROUNDED_SYSTEM_PROMPT + """

DODATKOWE ZASADY:
- Odpowiadaj po polsku
- Używaj punktów dla listy faktów
"""
```

---

## Przykłady odpowiedzi

### Odpowiedź z cytatami ✅

```
Pytanie: Jaki jest budżet projektu Alpha?

Odpowiedź: Budżet projektu Alpha wynosi 150,000 PLN, zatwierdzony
przez zarząd 15 listopada 2024.

[Źródło: email, 2024-11-15, "Budżet projektu Alpha w wysokości 150k PLN
został zatwierdzony..."]
[Źródło: note, 2024-11-16, "Notatka: Alpha - budżet 150,000 zaakceptowany"]
```

### Przyznanie się do niewiedzy ✅

```
Pytanie: Ile zarabia mój kolega Tomek?

Odpowiedź: Nie mogłem znaleźć informacji o zarobkach Tomka
w Twoich zindeksowanych dokumentach.

Ta informacja może nie być zapisana w Twoich notatkach,
e-mailach lub wiadomościach.
```

### Odpowiedź warunkowa ✅

```
Pytanie: Kiedy jest deadline projektu?

Odpowiedź: W Twoich dokumentach znalazłem różne daty deadline'u:

1. **Wstępny deadline**: 15 stycznia 2025
   [Źródło: email, 2024-10-01, "Planujemy zakończenie na 15.01..."]

2. **Przełożony deadline**: 31 marca 2025
   [Źródło: note, 2024-11-20, "Nowy deadline: koniec Q1 2025"]

Najnowsza informacja wskazuje na 31 marca 2025.
```

---

## Troubleshooting

### Problem: Brak cytatów w odpowiedzi

**Przyczyny:**
1. LLM ignoruje instrukcje z promptu
2. Brak pasujących dokumentów

**Rozwiązania:**
```python
# Sprawdź czy są dokumenty
result = engine.query("test", include_explanation=True)
print(f"Dokumentów pobranych: {len(result['explanation']['documents_retrieved'])}")

# Jeśli 0 — problem z wyszukiwaniem
# Jeśli >0 ale brak cytatów — problem z LLM
```

### Problem: Odpowiedzi "halucynują" mimo promptu

**Rozwiązania:**
1. Użyj silniejszego modelu (GPT-4, Claude 3)
2. Zmniejsz temperaturę LLM (jeśli konfigurowalna)
3. Dodaj więcej przykładów w prompcie

### Problem: Cytaty nie pasują do odpowiedzi

```python
# Włącz tryb debug
import logging
logging.getLogger("src.rag").setLevel(logging.DEBUG)

result = engine.query("...", include_explanation=True)
# Sprawdź które dokumenty zostały faktycznie użyte
```

---

## Powiązane

- **[FR-P0-4: Explainability](FR-P0-4-Explainability)** — zobacz dokładnie które fragmenty weszły do kontekstu
- **[Pipelines](Pipelines)** — jak działa pipeline RAG
- **[API Reference](API-Reference)** — pełna dokumentacja Citation i GroundedResponse

---

<p align="center">
  <a href="Podstawy-użytkowania">← Podstawy użytkowania</a> |
  <a href="Home">Strona główna</a> |
  <a href="FR-P0-2-Offline-Mode">FR-P0-2: Offline Mode →</a>
</p>
