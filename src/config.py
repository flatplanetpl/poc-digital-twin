"""Central configuration for Digital Twin application.

FR-P0-2: Offline / No-Leak Mode
- System can work without Internet
- Cloud LLM integrations can be completely disabled
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =========================================
# GPU Profile Presets
# =========================================
@dataclass(frozen=True)
class GpuPreset:
    """Configuration preset for a specific GPU capability level."""

    name: str
    description: str
    vram_gb: str  # Approximate VRAM requirement
    gpt4all_model: str
    top_k: int
    embedding_model: str


GPU_PRESETS: dict[str, GpuPreset] = {
    "low": GpuPreset(
        name="low",
        description="For integrated GPUs or CPU-only (4GB VRAM or less)",
        vram_gb="≤4GB",
        gpt4all_model="orca-mini-3b-gguf2-q4_0.gguf",
        top_k=3,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    ),
    "medium": GpuPreset(
        name="medium",
        description="For mid-range GPUs (6-8GB VRAM, e.g., RTX 3060, RTX 4060)",
        vram_gb="6-8GB",
        gpt4all_model="mistral-7b-instruct-v0.1.Q4_0.gguf",
        top_k=5,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    ),
    "high": GpuPreset(
        name="high",
        description="For high-end GPUs (12GB+ VRAM, e.g., RTX 3080, RTX 4080)",
        vram_gb="12-16GB",
        gpt4all_model="llama-2-13b-chat.ggmlv3.q4_0.bin",
        top_k=8,
        embedding_model="sentence-transformers/all-mpnet-base-v2",
    ),
    "ultra": GpuPreset(
        name="ultra",
        description="For enthusiast GPUs (24GB+ VRAM, e.g., RTX 4090, A100)",
        vram_gb="≥24GB",
        gpt4all_model="nous-hermes-llama2-13b.Q5_K_M.gguf",
        top_k=12,
        embedding_model="sentence-transformers/all-mpnet-base-v2",
    ),
}


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

    # =========================================
    # GPU Profile
    # =========================================
    gpu_profile: Literal["low", "medium", "high", "ultra"] | None = Field(
        default=None,
        description="GPU capability profile - overrides model/top_k settings when set",
    )

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

    # =========================================
    # GPU Profile Computed Properties
    # =========================================
    @property
    def gpu_preset(self) -> GpuPreset | None:
        """Get the GPU preset if a profile is configured."""
        if self.gpu_profile:
            return GPU_PRESETS.get(self.gpu_profile)
        return None

    @property
    def effective_gpt4all_model(self) -> str:
        """Get GPT4All model - from GPU profile or direct setting."""
        if preset := self.gpu_preset:
            return preset.gpt4all_model
        return self.gpt4all_model

    @property
    def effective_top_k(self) -> int:
        """Get TOP_K - from GPU profile or direct setting."""
        if preset := self.gpu_preset:
            return preset.top_k
        return self.top_k

    @property
    def effective_embedding_model(self) -> str:
        """Get embedding model - from GPU profile or direct setting."""
        if preset := self.gpu_preset:
            return preset.embedding_model
        return self.embedding_model

    def print_gpu_info(self) -> None:
        """Print current GPU configuration info."""
        if preset := self.gpu_preset:
            print(f"GPU Profile: {preset.name} ({preset.description})")
            print(f"  VRAM: {preset.vram_gb}")
            print(f"  Model: {preset.gpt4all_model}")
            print(f"  TOP_K: {preset.top_k}")
            print(f"  Embedding: {preset.embedding_model}")
        else:
            print("GPU Profile: None (using direct settings)")
            print(f"  Model: {self.gpt4all_model}")
            print(f"  TOP_K: {self.top_k}")
            print(f"  Embedding: {self.embedding_model}")


# Global settings instance
settings = Settings()
