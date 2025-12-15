"""Central configuration for Digital Twin application."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    data_dir: Path = Field(default=Path("./data"))
    storage_dir: Path = Field(default=Path("./storage"))

    # Qdrant
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="digital_twin")

    # Embedding
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # LLM
    llm_provider: Literal["gpt4all", "openai", "anthropic"] = Field(default="gpt4all")

    # GPT4All
    gpt4all_model: str = Field(default="mistral-7b-instruct-v0.1.Q4_0.gguf")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4-turbo")

    # Anthropic
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229")

    # RAG
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=50)
    top_k: int = Field(default=5)

    # UI
    streamlit_port: int = Field(default=8501)

    @property
    def db_path(self) -> Path:
        """Path to SQLite database for chat history."""
        return self.storage_dir / "chat_history.db"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
