# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Digital Twin is an offline AI assistant that processes personal data (notes, emails, WhatsApp chats, Facebook Messenger) using RAG (Retrieval-Augmented Generation). Supports both local LLM (GPT4All) and cloud APIs (OpenAI, Anthropic).

## Architecture

```
User Query → QueryPreprocessor → Embedding → Qdrant Search → Context + LLM → Response
                    ↓                ↓
            Extract filters    HuggingFace          GPT4All / OpenAI / Claude
            (person, date)     (all-MiniLM)
                    ↓
            ContactGraph ← ContactRegistry (SQLite)
```

Four layers:
1. **Data Processing** (`src/loaders/`) - Parse TXT, MD, EML, MBOX, WhatsApp TXT, Messenger JSON, FB Profile, Contacts, Location
2. **Vector Index** (`src/indexer/`) - Qdrant for embeddings with metadata filtering
3. **Contact Graph** (`src/graph/`) - Relationship tracking and contact statistics
4. **Conversational** (`src/rag/`, `src/llm/`) - LlamaIndex RAG + pluggable LLM providers + QueryPreprocessor

## Technology Stack

- **Framework**: LlamaIndex
- **Vector DB**: Qdrant (Docker)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **LLM**: GPT4All (default), OpenAI, Anthropic (configurable)
- **UI**: Streamlit
- **Storage**: SQLite (chat history)

## Common Commands

```bash
# Install
pip install -e .

# Start Qdrant
docker-compose up -d

# Index all data
python scripts/ingest.py --source ./data/

# Index only Facebook/Messenger data
python scripts/ingest.py --source ./data/messenger --types facebook

# Index specific data types
python scripts/ingest.py --source ./data/ --types messenger profile contacts

# Run UI
streamlit run src/ui/app.py
```

## Key Files

| File | Purpose |
|------|---------|
| `src/config.py` | Pydantic settings from .env |
| `src/loaders/base.py` | Abstract loader with Template Method pattern |
| `src/llm/factory.py` | LLM provider factory (Strategy pattern) |
| `src/rag/query_engine.py` | Main RAG pipeline orchestration |
| `src/rag/query_preprocessor.py` | Extract person/date/source filters from queries |
| `src/graph/contact_graph.py` | Contact relationship analysis service |
| `src/storage/contact_registry.py` | SQLite contact tracking and statistics |
| `src/ui/app.py` | Streamlit chat interface |

## Data Loaders

| Loader | Source Type | Formats |
|--------|-------------|---------|
| `TextLoader` | text | .txt, .md, .markdown |
| `EmailLoader` | email | .eml, .mbox |
| `WhatsAppLoader` | whatsapp | .txt (WhatsApp export) |
| `MessengerLoader` | messenger | .json (FB message_*.json) |
| `ProfileLoader` | profile | profile_information.json |
| `ContactsLoader` | contacts | your_friends.json, contacts_uploaded.json |
| `LocationLoader` | location | device_location.json, primary_location.json |
| `SearchHistoryLoader` | search_history | your_search_history.json |
| `AdsInterestsLoader` | interests | ads_interests.json |

## Configuration

All settings in `.env` (see `.env.example`):
- `LLM_PROVIDER`: gpt4all | openai | anthropic
- `QDRANT_HOST/PORT`: Vector DB connection
- `EMBEDDING_MODEL`: HuggingFace model name
- `CHUNK_SIZE/OVERLAP`: Document chunking params

## Design Patterns

- **Template Method**: `BaseLoader` defines skeleton, subclasses implement parsing
- **Strategy + Factory**: LLM providers with `create_llm()` factory
- **Repository**: `ChatHistory` for SQLite persistence
