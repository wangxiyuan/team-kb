from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SEARCH_SCOPES = ("guides", "community", "work", "skills", "records")
ARCHIVE_REL = Path("records") / "archive"


def _find_repo(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


@dataclass(frozen=True)
class KBConfig:
    repo: Path

    @property
    def templates_dir(self) -> Path:
        return self.repo / "templates"

    @property
    def skills_dir(self) -> Path:
        return self.repo / "skills"

    @property
    def docs_dir(self) -> Path:
        return self.repo / "docs"

    @property
    def records_dir(self) -> Path:
        return self.repo / "records"

    @property
    def archive_dir(self) -> Path:
        return self.repo / ARCHIVE_REL

    @property
    def pending_dir(self) -> Path:
        return self.repo / ".kb" / "pending"

    @property
    def usage_path(self) -> Path:
        return self.repo / ".kb" / "usage.json"

    @property
    def index_path(self) -> Path:
        return self.repo / "INDEX.md"

    def scope_dir(self, scope: str) -> Path:
        if scope == "skills":
            return self.skills_dir
        if scope == "records":
            return self.records_dir
        return self.docs_dir / scope

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.repo.resolve()).as_posix()

    def resolve_within_repo(self, relative_path: str) -> Path:
        target = (self.repo / relative_path).resolve()
        if target != self.repo.resolve() and self.repo.resolve() not in target.parents:
            raise ValueError(f"path escapes repository: {relative_path}")
        return target


def resolve_repo(explicit: str | None = None) -> KBConfig:
    for raw in (explicit, os.environ.get("TEAM_KB_REPO"), str(Path.cwd())):
        if not raw:
            continue
        candidate = Path(raw).expanduser().resolve()
        repo = _find_repo(candidate)
        if repo is not None:
            return KBConfig(repo=repo)
    raise RuntimeError("team-kb repository not found; pass --repo or set TEAM_KB_REPO")
