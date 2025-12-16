# Scenariusze użycia

Praktyczne i kreatywne przykłady wykorzystania Digital Twin w różnych kontekstach.

---

## Spis treści

1. [Scenariusze biznesowe](#scenariusze-biznesowe)
2. [Scenariusze osobiste](#scenariusze-osobiste)
3. [Scenariusze kreatywne](#scenariusze-kreatywne)
4. [Zaawansowane workflow'y](#zaawansowane-workflowy)

---

## Scenariusze biznesowe

### 1. Przygotowanie do spotkania z klientem

**Sytuacja:** Za godzinę masz spotkanie z klientem Acme Corp. Chcesz szybko przypomnieć sobie wszystkie ustalenia.

```python
from src.rag import RAGEngine

engine = RAGEngine()

# 1. Szybkie podsumowanie
result = engine.query(
    "Podsumuj wszystkie ustalenia z Acme Corp z ostatnich 3 miesięcy"
)
print(result["answer"])

# 2. Kluczowe decyzje
result = engine.query(
    "Jakie decyzje zostały podjęte w sprawie projektu z Acme Corp?"
)

# 3. Otwarte kwestie
result = engine.query(
    "Jakie kwestie pozostały nierozwiązane z Acme Corp?"
)

# 4. Kontakty i role
result = engine.query(
    "Kto jest kim w Acme Corp? Jakie są ich role?"
)
```

**Przykładowa odpowiedź:**
```
Na podstawie Twoich dokumentów, kluczowe ustalenia z Acme Corp:

📅 **Budżet i timeline:**
- Budżet: 150,000 PLN (zatwierdzony 15.11.2024)
  [Źródło: email, 2024-11-15, "Budżet zatwierdzony przez zarząd..."]
- Deadline: 31 marca 2025
  [Źródło: note, 2024-11-20, "Deadline Q1 2025 potwierdzony..."]

👥 **Zespół klienta:**
- PM: Anna Kowalska (anna@acme.com)
- Tech Lead: Marek Nowak
  [Źródło: email, 2024-10-05, "Przedstawiam zespół..."]

⚠️ **Otwarte kwestie:**
- Specyfikacja modułu raportowania (oczekuje na decyzję)
  [Źródło: whatsapp, 2024-12-10, "Czekamy na spec raportów..."]
```

---

### 2. Analiza historii komunikacji

**Sytuacja:** Chcesz zrozumieć jak ewoluowała współpraca z danym partnerem.

```python
# Chronologia współpracy
result = engine.query(
    "Przedstaw chronologicznie moją komunikację z firmą XYZ od początku"
)

# Zmiana tonu/relacji
result = engine.query(
    "Jak zmieniał się ton mojej komunikacji z XYZ w czasie?"
)

# Punkty zwrotne
result = engine.query(
    "Jakie były kluczowe momenty w mojej współpracy z XYZ?"
)
```

---

### 3. Rozliczanie czasu pracy (freelancer)

**Sytuacja:** Musisz przygotować raport dla klienta o wykonanych pracach.

```python
# Znajdź wszystkie wzmianki o projekcie
docs = engine.search("projekt Alpha", top_k=50)

# Podsumuj wykonane prace
result = engine.query(
    "Jakie prace wykonałem dla projektu Alpha w grudniu 2024?"
)

# Znajdź zobowiązania
result = engine.query(
    "Jakie zobowiązania podjąłem wobec klienta projektu Alpha?"
)
```

---

### 4. Due diligence przed współpracą

**Sytuacja:** Rozważasz współpracę z kimś, z kim miałeś kontakt w przeszłości.

```python
# Historia kontaktów
result = engine.query(
    "Jaka jest moja historia kontaktów z Janem Kowalskim?"
)

# Wrażenia i notatki
result = engine.query(
    "Jakie były moje wrażenia po spotkaniach z Janem Kowalskim?"
)

# Wspólne projekty
result = engine.query(
    "Czy pracowałem już z Janem Kowalskim? Jak to wyglądało?"
)
```

---

## Scenariusze osobiste

### 5. Osobisty dziennik AI

**Sytuacja:** Chcesz, żeby system rozumiał Twoje życie i pomagał w refleksji.

```python
# Analiza nastroju (wymaga notatek z tagami emocji)
result = engine.query(
    "Jak zmieniał się mój nastrój w tym tygodniu na podstawie moich notatek?"
)

# Wzorce
result = engine.query(
    "Jakie tematy najczęściej pojawiają się w moich notatkach?"
)

# Refleksja
result = engine.query(
    "Co było dla mnie najważniejsze w tym miesiącu?"
)

# Postępy w celach
result = engine.query(
    "Jaki postęp zrobiłem w realizacji moich celów na ten rok?"
)
```

---

### 6. Zarządzanie relacjami osobistymi

**Sytuacja:** Chcesz pamiętać ważne rzeczy o bliskich osobach.

```python
# Urodziny i ważne daty
result = engine.query(
    "Kiedy są urodziny moich najbliższych osób?"
)

# Preferencje
result = engine.query(
    "Co lubi moja mama? Jakie ma zainteresowania?"
)

# Historia rozmów
result = engine.query(
    "O czym rozmawiałem ostatnio z bratem?"
)
```

---

### 7. Planowanie podróży z historii

**Sytuacja:** Planujesz wyjazd do miejsca, które już odwiedzałeś.

```python
# Co pamiętasz z poprzedniej wizyty
result = engine.query(
    "Jakie były moje wrażenia z poprzedniego wyjazdu do Barcelony?"
)

# Rekomendacje
result = engine.query(
    "Jakie miejsca w Barcelonie poleciłbym na podstawie moich notatek?"
)

# Czego unikać
result = engine.query(
    "Czy były jakieś problemy podczas mojego pobytu w Barcelonie?"
)
```

---

### 8. Zdrowie i samopoczucie

**Sytuacja:** Śledzisz swoje zdrowie i chcesz znaleźć wzorce.

```python
# UWAGA: Użyj trybu offline dla danych medycznych!
# OFFLINE_MODE=true

# Wzorce
result = engine.query(
    "Kiedy najczęściej mam bóle głowy? Czy widzisz jakiś wzorzec?"
)

# Historia wizyt
result = engine.query(
    "Jakie były wyniki moich ostatnich badań?"
)

# Leki i dawkowanie
result = engine.query(
    "Jakie leki biorę i w jakich dawkach?"
)
```

---

## Scenariusze kreatywne

### 9. "Second Brain" dla freelancera

**Koncepcja:** Kompleksowy system zarządzania wiedzą o klientach i projektach.

**Struktura danych:**
```
data/
├── clients/
│   ├── acme/
│   │   ├── briefs/
│   │   ├── feedback/
│   │   ├── invoices/
│   │   └── notes/
│   └── beta/
├── projects/
│   ├── website_redesign/
│   │   ├── specs/
│   │   ├── meetings/
│   │   └── feedback/
│   └── mobile_app/
├── knowledge/
│   ├── tutorials/
│   ├── references/
│   └── lessons_learned/
└── admin/
    ├── contracts/
    └── finances/
```

**Przykładowe zapytania:**
```python
# Przychody
result = engine.query("Ile zarobiłem w tym kwartale?")

# Analiza projektów
result = engine.query("Które projekty miały najwięcej problemów? Dlaczego?")

# Lessons learned
result = engine.query("Jakie wnioski wyciągnąłem z poprzednich projektów?")

# Pipeline
result = engine.query("Jakie mam potencjalne projekty w pipeline?")
```

---

### 10. Asystent pisania w Twoim stylu

**Koncepcja:** System uczy się Twojego stylu pisania z historycznych dokumentów.

```python
# Analiza stylu
result = engine.query(
    "Jaki jest mój typowy styl pisania w emailach formalnych?"
)

# Przykłady
docs = engine.search("", source_type="email", top_k=20)
# Przeanalizuj wzorce: pozdrowienia, zakończenia, długość

# Pomoc w pisaniu (wymaga rozszerzenia P2: Drafting Mode)
result = engine.query(
    """Na podstawie moich poprzednich maili, pomóż mi napisać
    odpowiedź na tę wiadomość: [treść]"""
)
```

---

### 11. Archiwum rodzinne

**Koncepcja:** Przechowywanie i przeszukiwanie historii rodzinnej.

**Struktura:**
```
data/
├── family_stories/       # Spisane opowieści
├── letters/              # Zeskanowane listy
├── events/               # Notatki z wydarzeń
└── genealogy/            # Drzewo genealogiczne
```

**Zapytania:**
```python
# Historie
result = engine.query(
    "Co babcia opowiadała o czasach wojny?"
)

# Genealogia
result = engine.query(
    "Kim był pradziadek ze strony mamy? Co o nim wiem?"
)

# Tradycje
result = engine.query(
    "Jakie tradycje świąteczne ma nasza rodzina?"
)
```

---

### 12. Badacz / Naukowiec

**Koncepcja:** Organizacja notatek badawczych i literatury.

```python
# Przegląd literatury
result = engine.query(
    "Jakie są główne teorie w mojej dziedzinie badań?"
)

# Luki badawcze
result = engine.query(
    "Jakie luki badawcze zidentyfikowałem w literaturze?"
)

# Połączenia między ideami
result = engine.query(
    "Jak teoria X łączy się z moimi badaniami nad Y?"
)

# Cytaty
result = engine.query(
    "Jakie cytaty zebrałem na temat metodologii jakościowej?"
)
```

---

### 13. Dziennikarz / Pisarz

**Koncepcja:** Organizacja źródeł, wywiadów i materiałów.

```python
# Źródła na temat
result = engine.query(
    "Jakie źródła mam na temat zmiany klimatu?"
)

# Wywiady
result = engine.query(
    "Co powiedział ekspert X w wywiadzie o energii odnawialnej?"
)

# Sprawdzanie faktów
result = engine.query(
    "Jakie daty i liczby mam zweryfikowane w moich notatkach?"
)

# Cytaty do artykułu
result = engine.query(
    "Znajdź najlepsze cytaty na temat transformacji energetycznej"
)
```

---

## Zaawansowane workflow'y

### 14. Codzienny przegląd (Morning Review)

**Skrypt automatyzacji:**

```python
#!/usr/bin/env python3
"""Codzienny przegląd — uruchom rano."""

from src.rag import RAGEngine
from datetime import datetime, timedelta

engine = RAGEngine()

print("=" * 60)
print(f"☀️ PORANNY PRZEGLĄD — {datetime.now().strftime('%Y-%m-%d')}")
print("=" * 60)

# 1. Wczorajsze notatki
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
result = engine.query(f"Podsumuj moje notatki z {yesterday}")
print(f"\n📝 WCZORAJ:\n{result['answer']}")

# 2. Nadchodzące zobowiązania
result = engine.query("Jakie zobowiązania mam na najbliższe dni?")
print(f"\n📅 ZOBOWIĄZANIA:\n{result['answer']}")

# 3. Nierozwiązane kwestie
result = engine.query("Jakie sprawy pozostały otwarte?")
print(f"\n⚠️ OTWARTE SPRAWY:\n{result['answer']}")

# 4. Priorytety
result = engine.query("Co powinienem dziś traktować priorytetowo?")
print(f"\n🎯 PRIORYTETY:\n{result['answer']}")
```

---

### 15. Tygodniowy przegląd (Weekly Review)

```python
#!/usr/bin/env python3
"""Tygodniowy przegląd — uruchom w piątek/niedzielę."""

from src.rag import RAGEngine

engine = RAGEngine()

# Podsumowanie tygodnia
result = engine.query(
    "Podsumuj moje główne aktywności z tego tygodnia"
)

# Osiągnięcia
result = engine.query(
    "Co udało mi się osiągnąć w tym tygodniu?"
)

# Wnioski
result = engine.query(
    "Jakie wnioski mogę wyciągnąć z tego tygodnia?"
)

# Plan na przyszły tydzień
result = engine.query(
    "Co powinienem zaplanować na przyszły tydzień?"
)
```

---

### 16. Raport dla klienta

```python
#!/usr/bin/env python3
"""Generator raportu dla klienta."""

from src.rag import RAGEngine
from datetime import datetime

engine = RAGEngine()
client = "Acme Corp"
month = "grudzień 2024"

report = f"""
# RAPORT MIESIĘCZNY
Klient: {client}
Okres: {month}
Data: {datetime.now().strftime("%Y-%m-%d")}

## Wykonane prace
"""

result = engine.query(
    f"Jakie prace wykonałem dla {client} w {month}?"
)
report += result["answer"]

report += "\n\n## Kluczowe ustalenia\n"
result = engine.query(
    f"Jakie kluczowe ustalenia zostały podjęte z {client} w {month}?"
)
report += result["answer"]

report += "\n\n## Następne kroki\n"
result = engine.query(
    f"Jakie są zaplanowane następne kroki dla {client}?"
)
report += result["answer"]

# Zapisz raport
with open(f"report_{client}_{month}.md", "w") as f:
    f.write(report)
```

---

### 17. Analiza własnych decyzji

```python
#!/usr/bin/env python3
"""Analiza wzorców decyzyjnych."""

from src.rag import RAGEngine

engine = RAGEngine()
topic = "inwestowanie"

# Historia decyzji
result = engine.query(
    f"Jakie decyzje podejmowałem w sprawie {topic}?"
)
print(f"📊 HISTORIA DECYZJI:\n{result['answer']}")

# Wzorce
result = engine.query(
    f"Jakie wzorce widzisz w moich decyzjach o {topic}?"
)
print(f"\n🔍 WZORCE:\n{result['answer']}")

# Błędy
result = engine.query(
    f"Jakie błędy popełniłem w decyzjach o {topic}?"
)
print(f"\n⚠️ BŁĘDY:\n{result['answer']}")

# Wnioski
result = engine.query(
    f"Jakie wnioski mogę wyciągnąć o moim podejściu do {topic}?"
)
print(f"\n💡 WNIOSKI:\n{result['answer']}")
```

---

## Tips & tricks

### Efektywne zadawanie pytań

| ❌ Słabe pytanie | ✅ Dobre pytanie |
|------------------|------------------|
| "Projekt" | "Jakie są główne ustalenia projektu Alpha?" |
| "Anna" | "Kiedy ostatnio rozmawiałem z Anną i o czym?" |
| "Budżet" | "Jaki jest zatwierdzony budżet projektu X?" |
| "Spotkanie" | "Podsumuj moje ostatnie spotkanie z klientem Y" |

### Łączenie z automatyzacją

```bash
# Cron job — codzienny przegląd o 8:00
0 8 * * * cd /path/to/digital-twin && .venv/bin/python scripts/daily_review.py >> logs/daily.log

# Tygodniowy przegląd w piątek o 17:00
0 17 * * 5 cd /path/to/digital-twin && .venv/bin/python scripts/weekly_review.py >> logs/weekly.log
```

### Filtrowanie kontekstu

```python
# Tylko formalne dokumenty
result = engine.query(
    "Co ustalono?",
    source_type="email"  # Tylko e-maile, nie czaty
)

# Tylko ostatni miesiąc (wymaga rozszerzenia)
result = engine.query(
    "Co ustalono w ostatnim miesiącu?"
)
```

---

<p align="center">
  <a href="Pipelines">← Pipelines</a> |
  <a href="Home">Strona główna</a> |
  <a href="Integracje">Integracje →</a>
</p>
