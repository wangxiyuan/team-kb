from __future__ import annotations

import json
import subprocess
from typing import Any


def gh_api(path: str, params: dict[str, str] | None = None) -> Any:
    args = ["gh", "api", path]
    for key, value in (params or {}).items():
        args.extend(["-f", f"{key}={value}"])
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"gh api failed: {path}")
    return json.loads(completed.stdout)


def gh_search_prs(login: str, limit: int = 20) -> list[dict]:
    completed = subprocess.run(
        [
            "gh",
            "search",
            "prs",
            "--author",
            login,
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,url,repository,updatedAt,isDraft",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "gh search prs failed")
    return json.loads(completed.stdout)
