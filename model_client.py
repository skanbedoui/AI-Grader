"""Simple model client abstraction for the AI-Grader project.

Supports:
- Ollama local inference via HTTP
- OpenAI API via the official Python SDK

Usage:
    from model_client import generate_comment
    result = generate_comment(prompt, system_prompt)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI

from config import get_openai_api_key, get_openai_model, get_ollama_model, get_provider

load_dotenv()


@dataclass(frozen=True)
class ModelResponse:
    text: str
    usage: dict[str, int]


def _call_ollama(prompt: str, system_prompt: str | None = None) -> ModelResponse:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    if system_prompt:
        payload["system"] = system_prompt

    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return ModelResponse(
        text=data.get("response", ""),
        usage={
            "input_tokens": int(data.get("prompt_eval_count", 0)),
            "output_tokens": int(data.get("eval_count", 0)),
        },
    )


def _call_openai(prompt: str, system_prompt: str | None = None) -> ModelResponse:
    api_key = get_openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file or environment.")

    client = OpenAI(api_key=api_key)
    model = get_openai_model()

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    usage = completion.usage
    return ModelResponse(
        text=completion.choices[0].message.content or "",
        usage={
            "input_tokens": int(usage.prompt_tokens if usage else 0),
            "output_tokens": int(usage.completion_tokens if usage else 0),
        },
    )


def generate_response(prompt: str, system_prompt: str | None = None) -> ModelResponse:
    """Generate a response and preserve provider usage metadata."""
    provider = get_provider()
    if provider == "ollama":
        return _call_ollama(prompt, system_prompt)
    if provider == "openai":
        return _call_openai(prompt, system_prompt)
    raise ValueError(f"Unsupported provider: {provider}")


def generate_comment(prompt: str, system_prompt: str | None = None) -> str:
    """Generate a single review comment using the active provider."""
    return generate_response(prompt, system_prompt).text


def main() -> None:
    sample_prompt = "Code: def add(a, b):\n    return a + b\n\nComment on whether this code has a bug."
    sample_system = (
        "Review the code snippet and return exactly one concise professional review comment. "
        "If no issue is found, say so."
    )

    result = generate_comment(sample_prompt, sample_system)
    print(json.dumps({"provider": get_provider(), "output": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
