"""Runtime configuration for the OmniAssistant data platform."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings shared by ingestion, processing, and storage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OMNI_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"

    project_root: Path = Field(default=Path("."))
    data_root: Path = Field(default=Path("data"))
    seed_sources_path: Path = Field(
        default=Path("../Agent_Knowledge_Base/crawl/seed_sources.txt")
    )

    allowed_domains: tuple[str, ...] = (
        "hus.vnu.edu.vn",
        "tuyensinh.hus.vnu.edu.vn",
    )
    crawl_max_depth: int = 2
    crawl_timeout_seconds: float = 20.0
    crawl_max_retries: int = 3
    crawl_user_agent: str = "OmniAssistantDataCrawler/0.1 (+local academic project)"
    respect_robots_txt: bool = True

    embedding_model_name: str = "intfloat/multilingual-e5-small"
    embedding_fallback_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_device: str = "auto"
    qdrant_url: str = "http://localhost:6333"
    qdrant_local_path: Path = Path("data/features/qdrant_local")
    qdrant_memory_local_path: Path = Path("data/features/qdrant_memory_local")
    qdrant_collection: str = "omni_hus_chunks"

    @property
    def resolved_qdrant_local_path(self) -> Path:
        return (self.resolved_project_root / self.qdrant_local_path).resolve()

    @property
    def resolved_qdrant_memory_local_path(self) -> Path:
        return (self.resolved_project_root / self.qdrant_memory_local_path).resolve()

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def parse_allowed_domains(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(item.strip().lower() for item in value.split(",") if item.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item).strip().lower() for item in value if str(item).strip())
        raise TypeError("allowed_domains must be a comma-separated string or sequence")

    @property
    def resolved_project_root(self) -> Path:
        return self.project_root.resolve()

    @property
    def resolved_data_root(self) -> Path:
        return (self.resolved_project_root / self.data_root).resolve()

    @property
    def raw_web_root(self) -> Path:
        return self.resolved_data_root / "raw" / "web"

    @property
    def raw_pdf_root(self) -> Path:
        return self.resolved_data_root / "raw" / "pdf"

    @property
    def metadata_root(self) -> Path:
        return self.resolved_data_root / "metadata"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
