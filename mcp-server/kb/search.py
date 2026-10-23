from __future__ import annotations

import json
import shutil
import subprocess

from .config import DEFAULT_SEARCH_SCOPES, SEARCH_SCOPES, KBConfig
from .validate import split_document


def _existing_dirs(config: KBConfig, scope: list[str]) -> list[str]:
    dirs = []
    for name in scope:
        path = config.scope_dir(name)
        if path.exists():
            dirs.append(str(path))
    return dirs


def _file_tags(path) -> list[str]:
    try:
        meta, _ = split_document(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []
    tags = meta.get("tags") or []
    return [str(tag) for tag in tags] if isinstance(tags, list) else []


def _matches_tags(path, tags: list[str]) -> bool:
    if not tags:
        return True
    present = set(_file_tags(path))
    return bool(present.intersection(tags))


def _snippet(line: str, limit: int = 240) -> str:
    stripped = " ".join(line.split())
    return stripped[:limit]


def _search_rg(
    config: KBConfig,
    query: str,
    dirs: list[str],
    tags: list[str],
    top_k: int,
) -> list[dict]:
    if not shutil.which("rg"):
        return []
    completed = subprocess.run(
        ["rg", "--json", "-i", "--max-count", "3", query, *dirs],
        cwd=config.repo,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        return []

    results: list[dict] = []
    seen: set[str] = set()
    for raw in completed.stdout.splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "match":
            continue
        data = event.get("data", {})
        path = config.repo / data["path"]["text"]
        rel = config.relative(path)
        if rel in seen or not _matches_tags(path, tags):
            continue
        seen.add(rel)
        results.append(
            {
                "path": rel,
                "snippet": _snippet(data["lines"]["text"]),
                "line": data.get("line_number"),
            }
        )
        if len(results) >= top_k:
            break
    return results


def _search_fallback(
    config: KBConfig,
    query: str,
    scope: list[str],
    tags: list[str],
    top_k: int,
) -> list[dict]:
    needle = query.lower()
    results: list[dict] = []
    for name in scope:
        base = config.scope_dir(name)
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            if not _matches_tags(path, tags):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, start=1):
                if needle in line.lower():
                    results.append(
                        {
                            "path": config.relative(path),
                            "snippet": _snippet(line),
                            "line": number,
                        }
                    )
                    break
            if len(results) >= top_k:
                return results
    return results


def search(
    config: KBConfig,
    query: str,
    scope: list[str] | None = None,
    tags: list[str] | None = None,
    top_k: int = 10,
) -> list[dict]:
    scope = scope or list(DEFAULT_SEARCH_SCOPES)
    unknown = [name for name in scope if name not in SEARCH_SCOPES]
    if unknown:
        raise ValueError(f"unknown scope: {', '.join(unknown)}")
    dirs = _existing_dirs(config, scope)
    if not dirs or not query.strip():
        return []
    results = _search_rg(config, query, dirs, tags or [], top_k)
    if not results and not shutil.which("rg"):
        results = _search_fallback(config, query, scope, tags or [], top_k)
    return results
