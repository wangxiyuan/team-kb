from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from config import BotConfig
from kb.config import KBConfig


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


@pytest.fixture
def bot_config(tmp_path: Path) -> BotConfig:
    repo = tmp_path / "team-kb"
    repo.mkdir()
    source_templates = Path(__file__).resolve().parents[2] / "templates"
    shutil.copytree(source_templates, repo / "templates")
    for relative in ("skills", "docs/guides", "docs/community", "docs/work", "records"):
        (repo / relative).mkdir(parents=True, exist_ok=True)
    (repo / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "tester")
    _git(repo, "config", "user.email", "tester@example.com")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return BotConfig(
        repo=repo,
        upstream="vllm-project/vllm",
        members=("alice", "bob"),
        org="vllm-project",
        openai_base_url="",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        slack_webhook_url="",
    )


@pytest.fixture
def kb(bot_config: BotConfig) -> KBConfig:
    return KBConfig(repo=bot_config.repo)
