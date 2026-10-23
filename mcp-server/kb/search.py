from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from .config import DEFAULT_SEARCH_SCOPES, SEARCH_SCOPES, KBConfig
from .validate import split_document

TOKEN_SPLIT_RE = re.compile(r"\s+")


def _query_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in TOKEN_SPLIT_RE.split(query.strip()):
        token = raw.lower()
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


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


def _is_searchable(path: Path) -> bool:
    return path.name != "README.md"


def _snippet(line: str, limit: int = 240) -> str:
    stripped = " ".join(line.split())
    return stripped[:limit]


def _best_line(text: str, tokens: list[str]) -> tuple[str, int]:
    best_line = ""
    best_number = 1
    best_hits = -1
    for number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        hits = sum(1 for token in tokens if token in lowered)
        if hits > best_hits:
            best_hits = hits
            best_line = line
            best_number = number
    return _snippet(best_line), best_number


def _search_rg(
    config: KBConfig,
    needle: str,
    dirs: list[str],
    tags: list[str],
    top_k: int,
) -> list[dict]:
    if not shutil.which("rg"):
        return []
    completed = subprocess.run(
        ["rg", "--json", "-i", "-F", "--max-count", "3", needle, *dirs],
        cwd=config.repo,
        capture_output=True,
        text=True,
        check=False,
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
        if not _is_searchable(path):
            continue
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
    needle: str,
    scope: list[str],
    tags: list[str],
    top_k: int,
) -> list[dict]:
    results: list[dict] = []
    for name in scope:
        base = config.scope_dir(name)
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            if not _is_searchable(path) or not _matches_tags(path, tags):
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


def _score_file(path: Path, tokens: list[str]) -> tuple[list[str], str, int] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lowered = text.lower()
    present = [token for token in tokens if token in lowered]
    if not present:
        return None
    snippet, number = _best_line(text, present)
    return present, snippet, number


def _multi_token_scan(
    config: KBConfig,
    tokens: list[str],
    scope: list[str],
    tags: list[str],
    top_k: int,
) -> list[dict]:
    threshold = max(2, math.ceil(len(tokens) * 0.5))
    scored: list[tuple[int, str, dict]] = []
    for name in scope:
        base = config.scope_dir(name)
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            if not _is_searchable(path) or not _matches_tags(path, tags):
                continue
            matched = _score_file(path, tokens)
            if matched is None:
                continue
            present, snippet, number = matched
            if len(present) < threshold:
                continue
            scored.append(
                (
                    len(present),
                    config.relative(path),
                    {"snippet": snippet, "line": number},
                )
            )
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [{"path": rel, **payload} for _, rel, payload in scored[:top_k]]


def _multi_token_search(
    config: KBConfig,
    tokens: list[str],
    scope: list[str],
    dirs: list[str],
    tags: list[str],
    top_k: int,
) -> list[dict]:
    if not shutil.which("rg"):
        return _multi_token_scan(config, tokens, scope, tags, top_k)

    args = ["rg", "-l", "-i", "-F", "--no-messages"]
    for token in tokens:
        args.extend(["-e", token])
    args.extend(dirs)
    completed = subprocess.run(
        args, cwd=config.repo, capture_output=True, text=True, check=False
    )
    if completed.returncode not in (0, 1):
        return _multi_token_scan(config, tokens, scope, tags, top_k)

    threshold = max(2, math.ceil(len(tokens) * 0.5))
    scored: list[tuple[int, str, dict]] = []
    for raw in completed.stdout.splitlines():
        path = config.repo / raw
        if (
            not path.is_file()
            or not _is_searchable(path)
            or not _matches_tags(path, tags)
        ):
            continue
        matched = _score_file(path, tokens)
        if matched is None:
            continue
        present, snippet, number = matched
        if len(present) < threshold:
            continue
        scored.append(
            (
                len(present),
                config.relative(path),
                {"snippet": snippet, "line": number},
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [{"path": rel, **payload} for _, rel, payload in scored[:top_k]]


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
    tokens = _query_tokens(query)
    if not dirs or not tokens:
        return []

    tags = tags or []
    if len(tokens) > 1:
        return _multi_token_search(config, tokens, scope, dirs, tags, top_k)

    needle = tokens[0]
    results = _search_rg(config, needle, dirs, tags, top_k)
    if not results and not shutil.which("rg"):
        results = _search_fallback(config, needle, scope, tags, top_k)
    return results
