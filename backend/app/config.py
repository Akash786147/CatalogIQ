"""
Central configuration. Reads from environment / .env.
Nothing downstream should read os.environ directly - go through Settings.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CATALOGIQ_", env_file=".env", extra="ignore")

    # LLM providers. Any subset may be configured; "auto" tries them in
    # PROVIDER_ORDER (OpenRouter first for its 1M context, then Groq, then
    # Gemini), falling through on rate limits or errors.
    llm_provider: str = "auto"  # "auto" | "openrouter" | "groq" | "gemini"
    openrouter_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    # Model ids verified against each provider's /models listing. Groq needs an
    # explicit id; Gemini's "-latest" alias tracks the current flash model, so a
    # deprecation does not 404 the pipeline.
    openrouter_model: str = "stealth/ox-alpha"
    groq_model: str = "openai/gpt-oss-120b"
    gemini_model: str = "gemini-flash-latest"

    # where manufacturer spec-sheet text files live, if any (RAG corpus).
    # Each file: <manufacturer_slug>__<url-escaped-or-placeholder>.txt
    spec_corpus_dir: Path = Path(__file__).resolve().parents[2] / "data" / "specs"

    # cross-row consensus: minimum agreeing siblings before a value propagates
    min_consensus_siblings: int = 3
    consensus_agreement_ratio: float = 0.8

    # statistical outlier: flag values further than this many MADs from family median
    outlier_mad_threshold: float = 3.5

    # Ceiling on Stage 1 model calls per run. Classification is cached per
    # (distributor, description signature), so the sample needs ~20; this is a
    # backstop that keeps a first page load bounded on an unfamiliar dataset.
    max_classification_llm_calls: int = 60

    # Stage 1's grouped calls are independent, so they run concurrently.
    classification_concurrency: int = 8

    # fuzzy vocabulary match: below this score (0-100), reject rather than snap
    lov_fuzzy_threshold: int = 88

    # Comma-separated origins allowed to call this API cross-origin, for when
    # the frontend is deployed away from the backend. Localhost and *.vercel.app
    # are always permitted - see app/main.py.
    cors_origins: str = ""

    # Lives inside backend/ so the service is self-contained: a host told to
    # build from the `backend` directory (Railway, Docker) gets the sample
    # input and the delivery-format header in its image.
    data_dir: Path = Path(__file__).resolve().parents[1] / "data"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # raw_dir and output_dir must derive from data_dir at access time, not at
    # class-definition time - as plain fields they were bound to the default
    # once at import, so setting CATALOGIQ_DATA_DIR moved nothing.
    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def input_csv(self) -> Path:
        return self.raw_dir / "input_sample.csv"

    @property
    def delivery_format_csv(self) -> Path:
        return self.raw_dir / "delivery_format.csv"


# The unprefixed names (GROQ_API_KEY, GEMINI_API_KEY) are each vendor's own
# convention, so support them alongside the CATALOGIQ_-prefixed form.
#
# Settings' own env_file parsing applies env_prefix to .env entries too, which
# would only match CATALOGIQ_GROQ_API_KEY. load_dotenv() puts the raw names
# into os.environ first so both spellings resolve.
import os

from dotenv import load_dotenv

_ENV_PATHS = [
    Path(__file__).resolve().parents[1] / ".env",   # backend/.env
    Path(__file__).resolve().parents[2] / ".env",   # repo-root .env
]


@lru_cache
def get_settings() -> Settings:
    for env_path in _ENV_PATHS:
        if env_path.exists():
            load_dotenv(env_path, override=False)

    s = Settings()
    if not s.openrouter_api_key:
        s.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if not s.groq_api_key:
        s.groq_api_key = os.environ.get("GROQ_API_KEY")
    if not s.gemini_api_key:
        s.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return s
