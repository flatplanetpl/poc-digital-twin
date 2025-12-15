# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Digital Twin is an offline AI assistant that processes personal data (notes, emails, WhatsApp chats) using RAG (Retrieval-Augmented Generation). Supports both local LLM (GPT4All) and cloud APIs (OpenAI, Anthropic).

## Architecture

```
User Query → Embedding → Qdrant Search → Context + LLM → Response
                ↓
         HuggingFace          GPT4All / OpenAI / Claude
         (all-MiniLM)
```

Three layers:
1. **Data Processing** (`src/loaders/`) - Parse TXT, MD, EML, MBOX, WhatsApp TXT, Messenger JSON
2. **Vector Index** (`src/indexer/`) - Qdrant for embeddings with metadata filtering
3. **Conversational** (`src/rag/`, `src/llm/`) - LlamaIndex RAG + pluggable LLM providers

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

# Index data
python scripts/ingest.py --source ./data/

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
| `src/ui/app.py` | Streamlit chat interface |

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
