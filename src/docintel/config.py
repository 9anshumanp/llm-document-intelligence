from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class DISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DI_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("data/samples"))
    cache_dir: Path = Field(default=Path(".di_cache"))

    llm_model: str = Field(default="gpt-4o-mini")
    request_timeout_s: float = Field(default=45.0, ge=5.0, le=180.0)
    max_retries: int = Field(default=6, ge=0, le=10)

    chunk_size: int = Field(default=1200, ge=200, le=6000)
    chunk_overlap: int = Field(default=200, ge=0, le=2000)

    enable_cache: bool = Field(default=True)
    extraction_cache_ttl_s: int = Field(default=60 * 60 * 24 * 14)
    llm_cache_ttl_s: int = Field(default=60 * 60 * 24 * 7)

    otlp_endpoint: str | None = Field(default=None)
    service_name: str = Field(default="doc-intel-reference")

    max_rps: float = Field(default=3.0, ge=0.0, le=100.0)

def get_settings() -> DISettings:
    return DISettings()
