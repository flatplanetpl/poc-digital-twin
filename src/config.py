"""Central configuration for Digital Twin application.

FR-P0-2: Offline / No-Leak Mode
- System can work without Internet
- Cloud LLM integrations can be completely disabled
"""

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

    # =========================================
    # FR-P0-2: Offline Mode Configuration
    # =========================================
    offline_mode: bool = Field(
        default=False,
        description="Enable offline mode - only local LLM (gpt4all) allowed",
    )
    allow_cloud_llm: bool = Field(
        default=True,
        description="Allow cloud LLM providers (OpenAI, Anthropic)",
    )

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
    chunk_size: int = Field(default=1024)
    chunk_overlap: int = Field(default=100)
    top_k: int = Field(default=5)

    # UI
    streamlit_port: int = Field(default=8501)

    # =========================================
    # FR-P0-3: Priority Rules Configuration
    # =========================================
    priority_similarity_weight: float = Field(
        default=0.7,
        description="Weight for similarity score (0-1)",
    )
    priority_document_weight: float = Field(
        default=0.3,
        description="Weight for document priority (0-1)",
    )
    priority_recency_max_days: int = Field(
        default=365,
        description="Max age in days for recency decay calculation",
    )

    # =========================================
    # FR-P3-3: Audit Configuration
    # =========================================
    audit_enabled: bool = Field(
        default=True,
        description="Enable audit logging",
    )
    audit_queries: bool = Field(
        default=False,
        description="Log query operations (not query text, just metadata)",
    )

    @property
    def db_path(self) -> Path:
        """Path to SQLite database for chat history."""
        return self.storage_dir / "chat_history.db"

    @property
    def available_llm_providers(self) -> list[str]:
        """Get LLM providers available based on mode settings.

        FR-P0-2: In offline mode or if cloud LLMs disabled,
        only gpt4all is available.
        """
        if self.offline_mode or not self.allow_cloud_llm:
            return ["gpt4all"]
        return ["gpt4all", "openai", "anthropic"]

    @property
    def is_offline(self) -> bool:
        """Check if system is in offline mode."""
        return self.offline_mode or not self.allow_cloud_llm

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
