"""Runtime configuration for the AI-Grader project.

This module centralizes the model/provider selection used by the future harness.
It supports both an Ollama local model and an OpenAI API-backed model.
"""

from __future__ import annotations

import os


def provider_settings() -> dict[str, str]:
    """Return provider configuration from environment variables.

    Expected variables:
      - LLM_PROVIDER: 'ollama' or 'openai'
      - OLLAMA_BASE_URL: e.g. http://localhost:11434
      - OLLAMA_MODEL: e.g. llama3.1
      - OPENAI_API_KEY: your API key
      - OPENAI_MODEL: e.g. gpt-4o-mini
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider not in {"ollama", "openai"}:
        raise ValueError(
            "LLM_PROVIDER must be either 'ollama' or 'openai'. "
            f"Received: {provider!r}"
        )

    settings = {
        "provider": provider,
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.1"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }
    return settings


def get_provider() -> str:
    return provider_settings()["provider"]


def get_ollama_model() -> str:
    return provider_settings()["ollama_model"]


def get_openai_api_key() -> str:
    return provider_settings()["openai_api_key"]


def get_openai_model() -> str:
    return provider_settings()["openai_model"]


if __name__ == "__main__":
    print(provider_settings())
