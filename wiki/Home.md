# Digital Twin — Twój Osobisty Asystent AI

<p align="center">
  <img src="https://img.shields.io/badge/wersja-1.0%20P0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python">
  <img src="https://img.shields.io/badge/licencja-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/status-aktywny-brightgreen" alt="Status">
</p>

---

## Czym jest Digital Twin?

**Digital Twin** to osobisty asystent AI, który przetwarza Twoje prywatne dane — notatki, e-maile, wiadomości z WhatsApp i Messengera — i odpowiada na pytania **wyłącznie na podstawie Twoich dokumentów**. To jak posiadanie własnego "cyfrowego bliźniaka", który:

- **Pamięta wszystko** co mu powierzyłeś
- **Nigdy nie halucynuje** — odpowiada tylko tym, co wie z Twoich danych
- **Zawsze cytuje źródła** — wiesz skąd pochodzi każda informacja
- **Chroni Twoją prywatność** — może działać całkowicie offline

---

## Dlaczego Digital Twin?

### Problem z tradycyjnym AI

| Tradycyjne AI (ChatGPT, Claude) | Digital Twin |
|--------------------------------|--------------|
| Dane wysyłane do serwerów | **Przetwarzanie lokalne** (GPT4All) |
| Odpowiedzi z "wiedzy ogólnej" | **Tylko Twoje dokumenty** |
| Brak kontroli nad danymi | **Pełna kontrola** — usuń gdy chcesz |
| "Halucynacje" — wymyślone fakty | **Grounded Answers** — zawsze z cytatem |
| Czarna skrzynka | **Explainability** — widzisz dlaczego |

### Dla kogo?

- **Freelancerzy** — zarządzanie wiedzą o klientach i projektach
- **Badacze** — przeszukiwanie notatek i literatury
- **Prawnicy** — analiza dokumentów (offline!)
- **Dziennikarze** — organizacja źródeł i wywiadów
- **Każdy** — kto chce mieć "Second Brain" pod kontrolą

---

## Funkcje P0 Critical (v1.0)

Obecna wersja implementuje **5 krytycznych wymagań** stanowiących fundament zaufania i prywatności:

| Funkcja | Opis | Status |
|---------|------|--------|
| **[Grounded Answers](FR-P0-1-Grounded-Answers)** | Odpowiedzi tylko z Twoich danych + obowiązkowe cytaty | ✅ |
| **[Offline Mode](FR-P0-2-Offline-Mode)** | Praca bez internetu, dane nigdy nie opuszczają komputera | ✅ |
| **[Priority Rules](FR-P0-3-Priority-Rules)** | Inteligentne ważenie dokumentów (decyzje > notatki > czaty) | ✅ |
| **[Explainability](FR-P0-4-Explainability)** | Pełna transparentność — widzisz co weszło do kontekstu | ✅ |
| **[Forget/RTBF](FR-P0-5-Forget-RTBF)** | Prawo do bycia zapomnianym — usuń dane zgodnie z RODO | ✅ |

---

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                      Digital Twin                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Loaders │───►│ Indexer │───►│  Qdrant │◄───│   RAG   │  │
│  │ (parse) │    │ (embed) │    │(vectors)│    │ Engine  │  │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘  │
│       │                                            │       │
│       │         ┌─────────┐    ┌─────────┐        │       │
│       │         │ SQLite  │    │   LLM   │◄───────┘       │
│       │         │(history)│    │(GPT4All)│                │
│       │         └─────────┘    └─────────┘                │
│       │                                                    │
│  ┌────┴────────────────────────────────────────────────┐  │
│  │                    Data Sources                      │  │
│  │  📝 Notes  📧 Emails  💬 WhatsApp  📱 Messenger     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Stos technologiczny:**
- **Framework RAG**: LlamaIndex
- **Baza wektorowa**: Qdrant (Docker)
- **Embeddingi**: sentence-transformers/all-MiniLM-L6-v2
- **LLM**: GPT4All (offline) / OpenAI / Anthropic
- **UI**: Streamlit
- **Persystencja**: SQLite

---

## Quick Start

```bash
# 1. Klonuj repozytorium
git clone git@github.com:flatplanetpl/poc-digital-twin.git
cd poc-digital-twin

# 2. Zainstaluj zależności
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Uruchom Qdrant
docker-compose up -d

# 4. Skonfiguruj
cp .env.example .env

# 5. Zaimportuj dane
python scripts/ingest.py --source ./data/

# 6. Uruchom UI
streamlit run src/ui/app.py
```

Szczegóły: **[Instalacja](Instalacja)**

---

## Nawigacja Wiki

### Pierwsze kroki
- **[Instalacja](Instalacja)** — krok po kroku od zera
- **[Konfiguracja](Konfiguracja)** — wszystkie opcje `.env`
- **[Podstawy użytkowania](Podstawy-użytkowania)** — import danych, zadawanie pytań

### Funkcje P0 Critical
- **[FR-P0-1: Grounded Answers](FR-P0-1-Grounded-Answers)** — cytaty i uziemienie
- **[FR-P0-2: Offline Mode](FR-P0-2-Offline-Mode)** — praca bez internetu
- **[FR-P0-3: Priority Rules](FR-P0-3-Priority-Rules)** — ważenie dokumentów
- **[FR-P0-4: Explainability](FR-P0-4-Explainability)** — transparentność RAG
- **[FR-P0-5: Forget/RTBF](FR-P0-5-Forget-RTBF)** — usuwanie danych

### Zaawansowane
- **[Pipeline'y przetwarzania](Pipelines)** — jak dane przepływają przez system
- **[Scenariusze użycia](Scenariusze-użycia)** — praktyczne i kreatywne przykłady
- **[Integracje](Integracje)** — rozszerzenia i API
- **[API Reference](API-Reference)** — dokumentacja programistyczna

### Pomoc
- **[FAQ](FAQ)** — najczęstsze pytania
- **[Troubleshooting](Troubleshooting)** — rozwiązywanie problemów
- **[Słownik pojęć](Słownik)** — terminologia RAG i AI

---

## Roadmap

### P0 Critical (v1.0) ✅
- [x] Grounded Answers
- [x] Offline Mode
- [x] Priority Rules
- [x] Explainability
- [x] Forget/RTBF

### P1 Very Important (planowane)
- [ ] **Recall Mode** — "Co już o tym pisałem?"
- [ ] **Decision Support** — analiza opcji i ryzyk
- [ ] **Contrarian Mode** — wykrywanie sprzeczności
- [ ] **Profile Memory** — zapamiętywanie preferencji
- [ ] **Session Summaries** — podsumowania rozmów

### P2 Important (planowane)
- [ ] **Metadata-first Retrieval** — filtry przed wyszukiwaniem
- [ ] **Hybrid Search** — semantic + keyword (BM25)
- [ ] **Drafting Mode** — pisanie w Twoim stylu
- [ ] **Action Extraction** — wyciąganie zadań
- [ ] **Re-index & Migration** — zarządzanie schematami

### P3 Maintenance (planowane)
- [ ] **Ingestion Monitoring** — status importu
- [ ] **Retention Policies** — automatyczne archiwizowanie
- [ ] **Audit Trail** — pełna historia operacji
- [ ] **Export/Backup** — kopie zapasowe

---

## Licencja

MIT License — używaj, modyfikuj, dystrybuuj.

---

## Kontakt

- **Issues**: [GitHub Issues](https://github.com/flatplanetpl/poc-digital-twin/issues)
- **Dyskusje**: [GitHub Discussions](https://github.com/flatplanetpl/poc-digital-twin/discussions)

---

<p align="center">
  <strong>Digital Twin v1.0</strong><br>
  <em>"Twoja pamięć, Twoje dane, Twoja kontrola."</em>
</p>
