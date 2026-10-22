from __future__ import annotations

import httpx
from config import BotConfig


def notify(config: BotConfig, text: str) -> bool:
    if not config.slack_enabled:
        return False
    response = httpx.post(
        config.slack_webhook_url,
        json={"text": text},
        timeout=20,
    )
    return response.is_success
