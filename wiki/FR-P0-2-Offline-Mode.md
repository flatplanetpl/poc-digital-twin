# FR-P0-2: Offline Mode

**Status:** ✅ Zaimplementowane (v1.0)

Tryb offline gwarantuje, że **żadne Twoje dane nie opuszczą komputera** — nawet przypadkowo.

---

## Problem

Przy pracy z wrażliwymi danymi (dokumenty prawne, medyczne, finansowe, osobiste) istnieje ryzyko:

1. **Przypadkowe użycie API chmurowego** — dane wysłane do OpenAI/Anthropic
2. **Brak kontroli** — nie wiesz co zostało wysłane
3. **Compliance** — naruszenie RODO, tajemnicy zawodowej, NDA

**Przykład ryzyka:**

```python
# Przypadkowa zmiana providera...
engine.set_llm_provider("openai")

# ...a potem zapytanie o wrażliwe dane
engine.query("Jakie są warunki umowy z klientem X?")
# 😱 Treść umowy została właśnie wysłana do OpenAI!
```

---

## Rozwiązanie

Digital Twin oferuje **config-level protection** — tryb offline wymuszany przez konfigurację:

```bash
# W .env:
OFFLINE_MODE=true
```

Gdy tryb offline jest aktywny:
- ✅ Tylko `gpt4all` (lokalny) jest dostępny
- ❌ OpenAI, Anthropic — zablokowane
- ❌ Próba użycia → `OfflineModeError`

---

## Konfiguracja

### Pełny tryb offline

```bash
# .env
OFFLINE_MODE=true
```

Efekt:
- Tylko GPT4All dostępny
- Wszystkie dane przetwarzane lokalnie
- Brak połączeń wychodzących do API LLM

### Tryb "tylko lokalne"

```bash
# .env
OFFLINE_MODE=false
ALLOW_CLOUD_LLM=false
```

Efekt:
- Tylko GPT4All dostępny
- Ale system nie jest w "trybie offline" (inne funkcje mogą działać)

### Pełny dostęp (domyślny)

```bash
# .env
OFFLINE_MODE=false
ALLOW_CLOUD_LLM=true
```

Efekt:
- Wszystkie providery dostępne
- Użytkownik sam wybiera

---

## Macierz konfiguracji

| OFFLINE_MODE | ALLOW_CLOUD_LLM | gpt4all | openai | anthropic | Dane wysyłane? |
|:------------:|:---------------:|:-------:|:------:|:---------:|:--------------:|
| `false` | `true` | ✅ | ✅ | ✅ | Możliwe* |
| `false` | `false` | ✅ | ❌ | ❌ | Nie |
| `true` | `true`** | ✅ | ❌ | ❌ | Nie |
| `true` | `false` | ✅ | ❌ | ❌ | Nie |

\* Jeśli użytkownik wybierze cloud LLM
\*\* OFFLINE_MODE nadpisuje ALLOW_CLOUD_LLM

---

## Użycie w kodzie

### Sprawdzanie trybu

```python
from src.config import settings

# Czy system jest w trybie offline?
print(f"Offline mode: {settings.offline_mode}")
print(f"Allow cloud: {settings.allow_cloud_llm}")
print(f"Is offline: {settings.is_offline}")

# Dostępni providerzy
print(f"Dostępne LLM: {settings.available_llm_providers}")
```

### Obsługa OfflineModeError

```python
from src.llm import create_llm, OfflineModeError

try:
    llm = create_llm("openai")
except OfflineModeError as e:
    print(f"❌ Zablokowane: {e}")
    # Fallback do lokalnego
    llm = create_llm("gpt4all")
```

### Lista dostępnych providerów

```python
from src.llm import get_available_providers

providers = get_available_providers()
print(f"Możesz użyć: {providers}")

# W trybie offline: ['gpt4all']
# W trybie online: ['gpt4all', 'openai', 'anthropic']
```

### Dynamiczna zmiana trybu

```python
import os

# Włącz tryb offline programowo
os.environ["OFFLINE_MODE"] = "true"

# Reload settings
from src.config import Settings
settings = Settings()

print(f"Teraz offline: {settings.is_offline}")
```

---

## Wskaźniki w UI

Gdy tryb offline jest aktywny, interfejs Streamlit wyświetla ostrzeżenie:

```
┌─────────────────────────────────────────┐
│ ⚠️ TRYB OFFLINE                         │
│ Chmurowe LLM są wyłączone.              │
│ Wszystkie dane przetwarzane lokalnie.   │
└─────────────────────────────────────────┘
```

Dodatkowo w sidebarze:
- Przyciski OpenAI/Anthropic są **wyszarzone**
- Tooltip wyjaśnia dlaczego

---

## Scenariusze użycia

### Praca z dokumentami prawnymi

```bash
# Przed pracą:
export OFFLINE_MODE=true
streamlit run src/ui/app.py

# Teraz bezpieczne przeglądanie umów, NDA, itp.
```

### Analiza danych medycznych

```bash
# .env dla tej sesji
OFFLINE_MODE=true
LLM_PROVIDER=gpt4all
GPT4ALL_MODEL=mistral-7b-instruct-v0.1.Q4_0.gguf
```

### Demo bez internetu

```bash
# Na prezentacji bez WiFi
OFFLINE_MODE=true
python scripts/ingest.py --source ./demo-data/
streamlit run src/ui/app.py
# Wszystko działa lokalnie!
```

### Przełączanie trybu per-sesja

```bash
# Sesja 1: Praca z wrażliwymi danymi
OFFLINE_MODE=true streamlit run src/ui/app.py

# Sesja 2: Normalna praca (nowe okno terminala)
OFFLINE_MODE=false LLM_PROVIDER=openai streamlit run src/ui/app.py
```

---

## Implementacja techniczna

### Sprawdzanie w factory

```python
# src/llm/factory.py

_CLOUD_PROVIDERS = {"openai", "anthropic"}

def create_llm(provider: str | None = None) -> BaseLLM:
    provider = provider or settings.llm_provider

    # Sprawdź czy cloud provider jest dozwolony
    if provider in _CLOUD_PROVIDERS:
        if settings.offline_mode:
            raise OfflineModeError(
                f"Cannot use cloud LLM '{provider}' in offline mode. "
                f"Use 'gpt4all' or disable OFFLINE_MODE."
            )
        if not settings.allow_cloud_llm:
            raise OfflineModeError(
                f"Cloud LLM '{provider}' is disabled. "
                f"Set ALLOW_CLOUD_LLM=true or use 'gpt4all'."
            )

    # ... tworzenie providera
```

### Property w Settings

```python
# src/config.py

class Settings(BaseSettings):
    offline_mode: bool = False
    allow_cloud_llm: bool = True

    @property
    def available_llm_providers(self) -> list[str]:
        """Dostępni providerzy w obecnej konfiguracji."""
        if self.offline_mode or not self.allow_cloud_llm:
            return ["gpt4all"]
        return ["gpt4all", "openai", "anthropic"]

    @property
    def is_offline(self) -> bool:
        """Czy system jest efektywnie offline."""
        return self.offline_mode or not self.allow_cloud_llm
```

---

## Bezpieczeństwo

### Co jest chronione?

| Komponent | W trybie online | W trybie offline |
|-----------|-----------------|------------------|
| Embeddingi | Lokalnie (HuggingFace) | Lokalnie |
| Wyszukiwanie (Qdrant) | Lokalnie | Lokalnie |
| Generowanie (LLM) | Cloud lub lokalnie | Tylko lokalnie |
| Historia czatów | Lokalnie (SQLite) | Lokalnie |
| Audyt | Lokalnie (SQLite) | Lokalnie |

### Co NIE jest chronione przez offline mode?

- **Pobieranie modeli** — pierwszy raz model GPT4All jest pobierany z internetu
- **Aktualizacje** — `pip install` wymaga internetu
- **Inne połączenia** — system nie blokuje całego internetu, tylko API LLM

### Pełna izolacja sieciowa

Dla maksymalnej ochrony możesz:

```bash
# 1. Pobierz model wcześniej
mkdir -p ~/.cache/gpt4all
wget -O ~/.cache/gpt4all/mistral-7b-instruct-v0.1.Q4_0.gguf \
  https://gpt4all.io/models/gguf/mistral-7b-instruct-v0.1.Q4_0.gguf

# 2. Odłącz od sieci
nmcli networking off  # Linux
# lub fizycznie odłącz kabel/WiFi

# 3. Uruchom w trybie offline
OFFLINE_MODE=true streamlit run src/ui/app.py
```

---

## Troubleshooting

### Problem: "OfflineModeError" przy starcie

```bash
# Sprawdź konfigurację
cat .env | grep -E "OFFLINE|ALLOW_CLOUD|LLM_PROVIDER"

# Jeśli LLM_PROVIDER=openai i OFFLINE_MODE=true → błąd
# Rozwiązanie:
LLM_PROVIDER=gpt4all
```

### Problem: GPT4All wolny w trybie offline

To normalne — lokalny model jest wolniejszy niż API chmurowe.

**Optymalizacje:**
1. Użyj mniejszego modelu: `GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf`
2. Zmniejsz TOP_K: mniej kontekstu = szybsza odpowiedź
3. Rozważ GPU (kompilacja z CUDA)

### Problem: Chcę czasem używać OpenAI

```bash
# Stwórz dwa pliki konfiguracji

# .env.offline (dla wrażliwych danych)
OFFLINE_MODE=true
LLM_PROVIDER=gpt4all

# .env.online (normalna praca)
OFFLINE_MODE=false
LLM_PROVIDER=openai

# Przełączaj przez:
cp .env.offline .env
# lub
cp .env.online .env
```

---

## Powiązane

- **[Konfiguracja](Konfiguracja)** — wszystkie opcje .env
- **[FR-P0-5: Forget/RTBF](FR-P0-5-Forget-RTBF)** — usuwanie danych (dla pełnej kontroli)
- **[Instalacja](Instalacja)** — jak zainstalować GPT4All

---

<p align="center">
  <a href="FR-P0-1-Grounded-Answers">← FR-P0-1: Grounded Answers</a> |
  <a href="Home">Strona główna</a> |
  <a href="FR-P0-3-Priority-Rules">FR-P0-3: Priority Rules →</a>
</p>
