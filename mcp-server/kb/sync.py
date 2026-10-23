from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from .config import KBConfig


class SyncError(Exception):
    pass


def git(
    config: KBConfig, *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=config.repo,
        capture_output=True,
        text=True,
        check=check,
    )


def pull(config: KBConfig) -> bool:
    completed = git(config, "pull", "--rebase", "--autostash", check=False)
    if completed.returncode != 0:
        return False
    marker = config.repo / ".kb" / "last_sync"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        datetime.now().astimezone().isoformat(timespec="seconds"),
        encoding="utf-8",
    )
    return True


def push(config: KBConfig) -> bool:
    completed = git(config, "push", "origin", "HEAD", check=False)
    return completed.returncode == 0


def head(config: KBConfig) -> str | None:
    completed = git(config, "rev-parse", "HEAD", check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def current_branch(config: KBConfig) -> str | None:
    completed = git(config, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def remote_head(config: KBConfig, branch: str = "main") -> str | None:
    completed = git(config, "rev-parse", f"origin/{branch}", check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def ahead_behind(config: KBConfig, branch: str = "main") -> tuple[int, int]:
    completed = git(
        config,
        "rev-list",
        "--left-right",
        "--count",
        f"origin/{branch}...HEAD",
        check=False,
    )
    if completed.returncode != 0:
        return 0, 0
    behind, ahead = completed.stdout.split()
    return int(ahead), int(behind)


def commit_paths(config: KBConfig, paths: list[Path], message: str) -> str | None:
    relatives = [config.relative(path) for path in paths]
    git(config, "add", "--", *relatives)
    staged = git(config, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return None
    git(config, "commit", "-m", message)
    return head(config)


def queue_pending(config: KBConfig, commit: str) -> Path:
    config.pending_dir.mkdir(parents=True, exist_ok=True)
    path = config.pending_dir / f"{int(time.time() * 1000)}-{commit[:12]}.json"
    path.write_text(
        json.dumps({"commit": commit, "created": time.time()}), encoding="utf-8"
    )
    return path


def list_pending(config: KBConfig) -> list[dict]:
    if not config.pending_dir.exists():
        return []
    items = []
    for path in sorted(config.pending_dir.glob("*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return items


def flush_pending(config: KBConfig) -> dict:
    pushed = 0
    while True:
        items = list_pending(config)
        if not items:
            break
        pull(config)
        if not push(config):
            break
        for item in items:
            for path in config.pending_dir.glob(f"*{item['commit'][:12]}.json"):
                path.unlink(missing_ok=True)
            pushed += 1
    remaining = list_pending(config)
    return {"pushed": pushed, "remaining": len(remaining), "pending": remaining}


def sync(config: KBConfig, pull_remote: bool = True, push_pending: bool = True) -> dict:
    pulled = pull(config) if pull_remote else False
    result = {"pulled": pulled, "pushed": 0, "conflicts": [], "pending": []}
    if push_pending:
        flushed = flush_pending(config)
        result["pushed"] = flushed["pushed"]
        result["pending"] = flushed["pending"]
    return result


def publish_commit(config: KBConfig, commit: str) -> dict:
    if push(config):
        return {"pushed": True, "queued": False}
    queue_pending(config, commit)
    return {"pushed": False, "queued": True}
