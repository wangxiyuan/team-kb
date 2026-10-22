from __future__ import annotations

import httpx
from config import BotConfig


def summarize(config: BotConfig, prompt: str, system: str | None = None) -> str | None:
    if not config.llm_enabled:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = httpx.post(
        f"{config.openai_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {config.openai_api_key}"},
        json={"model": config.openai_model, "messages": messages, "temperature": 0.2},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
