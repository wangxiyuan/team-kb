from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from kb.config import KBConfig

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "templates", repo / "templates")
    (repo / "skills").mkdir()
    (repo / "docs" / "guides").mkdir(parents=True)
    (repo / "records").mkdir()
    (repo / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "tester")
    _git(repo, "config", "user.email", "tester@example.com")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")


@pytest.fixture
def kb_repo(tmp_path: Path) -> KBConfig:
    repo = tmp_path / "team-kb"
    _init_repo(repo)
    return KBConfig(repo=repo)


@pytest.fixture
def kb_repo_with_origin(tmp_path: Path) -> KBConfig:
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(origin)],
        check=True,
        capture_output=True,
    )
    repo = tmp_path / "team-kb"
    _init_repo(repo)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")
    return KBConfig(repo=repo)
