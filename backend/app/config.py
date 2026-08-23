"""Settings, loaded from the repo-root .env. See .env.example."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_prefix="CATALOGIQ_",
        extra="ignore",
    )

    # Anthropic key is read without the CATALOGIQ_ prefix by convention.
    anthropic_api_key: str = ""
    model: str = "claude-sonnet-5"
    llm_enabled: bool = True

    data_dir: Path = REPO_ROOT / "data"
    output_dir: Path = REPO_ROOT / "data" / "output"
    db_path: Path = REPO_ROOT / "data" / "catalogiq.sqlite"

    max_concurrency: int = 8
    confidence_threshold: float = 0.85

    api_port: int = 8000

    @property
    def sample_input(self) -> Path:
        return self.data_dir / "raw" / "input_sample.csv"

    @property
    def delivery_format(self) -> Path:
        return self.data_dir / "raw" / "delivery_format.csv"

    @property
    def llm_available(self) -> bool:
        """LLM stages no-op cleanly when there is no key, so the pipeline still runs."""
        return self.llm_enabled and bool(self.anthropic_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    import os

    settings = Settings()
    # ANTHROPIC_API_KEY is the SDK's own conventional name; honour it too.
    if not settings.anthropic_api_key:
        settings.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings
