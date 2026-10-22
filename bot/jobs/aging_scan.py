from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from config import BotConfig
from kb.config import KBConfig
from kb.index import list_skills, write_index
from kb.sync import commit_paths, git, publish_commit
from kb.validate import split_document, validate_document
from notify import notify

RETENTION_DAYS = 30
STALE_DAYS = 180


def _archive_candidates(config: BotConfig, now: datetime) -> list[Path]:
    repo = KBConfig(config.repo)
    cutoff = now - timedelta(days=RETENTION_DAYS)
    moved: list[Path] = []
    if not repo.records_dir.exists():
        return moved

    for path in sorted(repo.records_dir.rglob("*.md")):
        if "archive" in path.parts:
            continue
        try:
            meta, _ = split_document(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        try:
            when = datetime.fromisoformat(str(meta.get("time")))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when >= cutoff:
            continue
        relative = path.relative_to(repo.records_dir)
        target = repo.archive_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        git(repo, "mv", repo.relative(path), repo.relative(target))
        moved.append(target)
    return moved


def _stale_report(config: BotConfig, now: datetime) -> Path:
    repo = KBConfig(config.repo)
    stale = [skill for skill in list_skills(repo) if skill["stale"]]
    iso = now.isocalendar()
    label = f"{iso.year}-W{iso.week:02d}"
    lines = [
        (
            f"- {skill['name']}（owner: {skill['owner'] or 'unknown'}，"
            f"本地使用 {skill['usage']} 次）"
        )
        for skill in stale
    ] or ["- 无过期 skill"]
    content = f"""---
title: 知识老化报告 {label}
date: {now.date().isoformat()}
author: team-kb-bot
status: active
tags: [aging]
---

# 知识老化报告 {label}

## 正文

超过 {STALE_DAYS} 天未更新的 skills：

{chr(10).join(lines)}

处理建议：更新、标 superseded，或在周复盘决定删除。
"""
    validate_document(repo, "note", content)
    target = repo.docs_dir / "work" / f"stale-skills-{label}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def run(config: BotConfig) -> dict:
    repo = KBConfig(config.repo)
    now = datetime.now(UTC)

    moved = _archive_candidates(config, now)
    stale_doc = _stale_report(config, now)
    index_path = write_index(repo)

    commit = commit_paths(
        repo,
        [*moved, stale_doc, index_path],
        "aging: archive records, refresh stale report and index",
    )
    publish = (
        publish_commit(repo, commit) if commit else {"pushed": True, "queued": False}
    )
    if publish["pushed"]:
        notify(
            config,
            f"[team-kb] aging 完成：归档 {len(moved)} 条记录，索引已刷新。",
        )
    return {
        "archived": len(moved),
        "stale_report": repo.relative(stale_doc),
        "pushed": publish["pushed"],
    }
