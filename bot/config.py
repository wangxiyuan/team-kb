from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from kb.config import resolve_repo


@dataclass(frozen=True)
class BotConfig:
    repo: Path
    upstream: str
    members: tuple[str, ...]
    org: str
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    slack_webhook_url: str

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_base_url and self.openai_api_key)

    @property
    def slack_enabled(self) -> bool:
        return bool(self.slack_webhook_url)


def load() -> BotConfig:
    config = resolve_repo(os.environ.get("TEAM_KB_REPO"))
    return BotConfig(
        repo=config.repo,
        upstream=os.environ.get("TEAM_KB_UPSTREAM", "vllm-project/vllm"),
        members=tuple(
            member.strip()
            for member in os.environ.get("TEAM_KB_MEMBERS", "").split(",")
            if member.strip()
        ),
        org=os.environ.get("TEAM_KB_ORG", "vllm-project"),
        openai_base_url=os.environ.get("OPENAI_BASE_URL", "").rstrip("/"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL", ""),
    )
