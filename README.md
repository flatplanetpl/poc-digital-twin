# Digital Twin

Offline AI assistant that processes your personal data (notes, emails, chats) using RAG (Retrieval-Augmented Generation). Designed with privacy in mind - runs entirely locally without external API calls (optional cloud LLM support).

## Features

- **Multi-source data ingestion**: Text files (TXT, MD), emails (EML, MBOX), WhatsApp exports, Messenger JSON
- **Semantic search**: Find relevant information across all your data
- **Conversational interface**: Chat with your data using natural language
- **Multiple LLM backends**: Local GPT4All (offline) or cloud APIs (OpenAI, Anthropic)
- **Conversation history**: Persistent chat sessions across restarts
- **Privacy-first**: All data stays on your machine (when using local LLM)

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (for Qdrant)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd digital-twin

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env

# Start Qdrant
docker-compose up -d
```

### Usage

1. **Add your data** to the `data/` directory:
   - Text files: `.txt`, `.md`
   - Emails: `.eml`, `.mbox`
   - WhatsApp: exported `.txt` files
   - Messenger: JSON export from Facebook (entire `inbox/` folder)

2. **Index your data**:
   ```bash
   python scripts/ingest.py
   ```

3. **Start the UI**:
   ```bash
   streamlit run src/ui/app.py
   ```

4. Open http://localhost:8501 in your browser

## Configuration

Edit `.env` to customize:

```env
# LLM Provider (gpt4all | openai | anthropic)
LLM_PROVIDER=gpt4all

# For cloud providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Project Structure

```
digital-twin/
├── src/
│   ├── config.py           # Configuration
│   ├── loaders/            # Data loaders
│   ├── indexer/            # Qdrant integration
│   ├── llm/                # LLM providers
│   ├── rag/                # RAG pipeline
│   ├── storage/            # Chat history
│   └── ui/                 # Streamlit app
├── scripts/
│   ├── ingest.py           # Data indexing CLI
│   └── run_ui.py           # UI launcher
├── data/                   # Your data files
└── storage/                # SQLite database
```

## Commands

```bash
# Index data
python scripts/ingest.py --source ./data/

# Index specific types
python scripts/ingest.py --types text email messenger

# Reset index and re-ingest
python scripts/ingest.py --reset

# Show index stats
python scripts/ingest.py --stats

# Run UI
streamlit run src/ui/app.py
```

## License

MIT
