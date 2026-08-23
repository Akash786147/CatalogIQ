"""
Thin wrapper around the hosted LLM providers we use: Groq and Gemini.

Every call site in the pipeline is expected to catch LLMUnavailable and fall
back to a deterministic heuristic or to BLANK_FLAGGED - the pipeline must run
headless end-to-end even with no API key configured, which is the actual
evaluation condition (see docs/00-brief.md). The LLM is a sparse enhancement
layer, not a hard dependency: it classifies, it names abbreviation-grammar
slots once per family, and it extracts from retrieved document chunks. It
never freely writes attribute values or descriptions.

Three providers, tried in order, so a rate limit on one does not stop a run:
  openrouter - OpenAI-compatible; default model has a 1M context window
  groq       - OpenAI-compatible chat completions, very fast
  gemini     - Google Generative Language API

Both are called over plain HTTP rather than via their SDKs. The request
shapes are small and stable, and it keeps the dependency list to httpx
instead of two more vendor packages.

Configure any subset of:
  OPENROUTER_API_KEY=...
  GROQ_API_KEY=...
  GEMINI_API_KEY=...        (GOOGLE_API_KEY also accepted)
"""
from __future__ import annotations

import json

import httpx

from app.config import get_settings


class LLMUnavailable(Exception):
    """Raised when no provider is configured, or every configured one failed."""


# running token tracking for the run report
usage_log: list[dict] = []

# Order the providers are tried in when llm_provider is "auto". OpenRouter
# leads on context window; Groq is the fast fallback; Gemini backs both up.
PROVIDER_ORDER = ("openrouter", "groq", "gemini")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Both default models reason before answering, so a tight budget can be spent
# entirely on thinking and return empty content. Never ask for less than this.
_MIN_TOKENS = 256


def _providers() -> list[str]:
    """Configured providers, in the order they should be tried."""
    settings = get_settings()
    preferred = (settings.llm_provider or "auto").lower()
    keys = {
        "openrouter": settings.openrouter_api_key,
        "groq": settings.groq_api_key,
        "gemini": settings.gemini_api_key,
    }
    available = [p for p in PROVIDER_ORDER if keys.get(p)]

    if preferred in PROVIDER_ORDER:
        # explicit choice first, but still fall back to the others if it fails
        return [p for p in [preferred] if p in available] + [
            p for p in available if p != preferred
        ]
    return available


def _call_openrouter(system: str, user: str, max_tokens: int) -> str:
    settings = get_settings()
    resp = httpx.post(
        OPENROUTER_URL,
        timeout=_TIMEOUT,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            # OpenRouter uses these for app attribution on its rankings page.
            "HTTP-Referer": "https://github.com/catalogiq",
            "X-Title": "CatalogIQ",
        },
        json={
            "model": settings.openrouter_model,
            "max_tokens": max(max_tokens, _MIN_TOKENS),
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
    )
    resp.raise_for_status()
    data = resp.json()
    # OpenRouter returns HTTP 200 with an `error` body on upstream failures.
    if data.get("error"):
        raise ValueError(str(data["error"]))
    usage = data.get("usage") or {}
    usage_log.append({
        "provider": "openrouter",
        "model": settings.openrouter_model,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    })
    return data["choices"][0]["message"]["content"] or ""


def _call_groq(system: str, user: str, max_tokens: int) -> str:
    settings = get_settings()
    resp = httpx.post(
        GROQ_URL,
        timeout=_TIMEOUT,
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={
            "model": settings.groq_model,
            "max_tokens": max(max_tokens, _MIN_TOKENS),
            "temperature": 0,
            # gpt-oss is a reasoning model: without this it can spend the whole
            # budget thinking and return empty content on short calls.
            "reasoning_effort": "low",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
    )
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage") or {}
    usage_log.append({
        "provider": "groq",
        "model": settings.groq_model,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    })
    return data["choices"][0]["message"]["content"] or ""


def _call_gemini(system: str, user: str, max_tokens: int) -> str:
    settings = get_settings()
    resp = httpx.post(
        GEMINI_URL.format(model=settings.gemini_model),
        timeout=_TIMEOUT,
        headers={"x-goog-api-key": settings.gemini_api_key},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max(max_tokens, _MIN_TOKENS),
                # same reasoning-budget concern as Groq, see _MIN_TOKENS
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
    )
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usageMetadata") or {}
    usage_log.append({
        "provider": "gemini",
        "model": settings.gemini_model,
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    })
    candidates = data.get("candidates") or []
    if not candidates:
        # safety block or empty response - treat as a failure so we fall through
        raise ValueError(f"gemini returned no candidates: {data.get('promptFeedback')}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


_CALLERS = {
    "openrouter": _call_openrouter,
    "groq": _call_groq,
    "gemini": _call_gemini,
}


def complete(system: str, user: str, max_tokens: int = 512) -> str:
    """Single-turn completion. Tries each configured provider in order.

    Raises LLMUnavailable if none is configured or all of them fail, which the
    caller treats as "no LLM" and falls back to its deterministic path.
    """
    providers = _providers()
    if not providers:
        raise LLMUnavailable(
            "No LLM provider configured "
            "(set OPENROUTER_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY)"
        )

    errors = []
    for name in providers:
        try:
            return _CALLERS[name](system, user, max_tokens)
        except Exception as e:  # network error, rate limit, bad key, safety block
            errors.append(f"{name}: {e}")
    raise LLMUnavailable("; ".join(errors))


def complete_json(system: str, user: str, max_tokens: int = 512) -> dict:
    """Completion that expects a single JSON object back. Strips code fences defensively."""
    raw = complete(system, user, max_tokens=max_tokens)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    # Models sometimes wrap the object in a sentence; salvage the outermost braces.
    if not cleaned.startswith("{"):
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"model did not return valid JSON: {e}") from e


def is_configured() -> bool:
    return bool(_providers())


def active_provider() -> str | None:
    """Which provider a call would use right now. None when unconfigured."""
    providers = _providers()
    return providers[0] if providers else None
