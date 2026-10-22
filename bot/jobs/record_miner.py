from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from config import BotConfig
from digest_generator import summarize
from kb.config import KBConfig
from kb.sync import commit_paths, publish_commit
from kb.validate import split_document, validate_document
from notify import notify

LOOKBACK_DAYS = 30


def collect(config: BotConfig, now: datetime | None = None) -> dict[str, list[dict]]:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=LOOKBACK_DAYS)
    found: dict[str, list[dict]] = defaultdict(list)

    repo = KBConfig(config.repo)
    if not repo.records_dir.exists():
        return found

    for path in sorted(repo.records_dir.rglob("*.md")):
        if "archive" in path.parts:
            continue
        try:
            meta, body = split_document(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not meta.get("potential_skill"):
            continue
        raw_time = meta.get("time")
        try:
            when = datetime.fromisoformat(str(raw_time))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when < since:
            continue
        found[str(meta.get("area", "other"))].append(
            {
                "path": repo.relative(path),
                "task": meta.get("task", ""),
                "time": raw_time,
                "body": body.strip()[:800],
            }
        )
    return found


def render(
    config: BotConfig, candidates: dict[str, list[dict]], now: datetime | None = None
) -> str:
    now = now or datetime.now(UTC)
    iso = now.isocalendar()
    label = f"{iso.year}-W{iso.week:02d}"

    sections = []
    for area, items in sorted(candidates.items()):
        lines = [
            f"- {item['task']}（{item['time']}，`{item['path']}`）" for item in items
        ]
        sections.append(f"### {area}\n\n" + "\n".join(lines))

    digest = "\n\n".join(sections) or "- 本周无候选"
    suggestion = summarize(
        config,
        f"Based on these engineering records, propose at most 3 reusable "
        f"skills or pitfalls the team should codify. "
        f"Answer in Chinese with concrete titles:\n{digest}",
        system=(
            "You are a vLLM team tech lead who turns raw work logs into reusable SOPs."
        ),
    )

    return f"""---
title: 沉淀候选 {label}
date: {now.date().isoformat()}
author: team-kb-bot
status: active
tags: [sediment-candidates]
---

# 沉淀候选 {label}

## 正文

以下来自本周期的 consented records（`potential_skill: true`），
供周复盘决策是否沉淀为 skill / pitfall。

{digest}

### bot 建议

{suggestion or "- 未配置 LLM，人工判断。"}
"""


def run(config: BotConfig) -> dict:
    repo = KBConfig(config.repo)
    now = datetime.now(UTC)
    candidates = collect(config, now)
    if not candidates:
        return {"candidates": 0, "wrote": None}

    content = render(config, candidates, now)
    validate_document(repo, "note", content)

    iso = now.isocalendar()
    target = (
        repo.docs_dir / "guides" / f"sediment-candidates-{iso.year}-W{iso.week:02d}.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    commit = commit_paths(repo, [target], "guides: sediment candidates")
    publish = (
        publish_commit(repo, commit) if commit else {"pushed": True, "queued": False}
    )
    if publish["pushed"]:
        notify(
            config,
            (
                f"[team-kb] 本周沉淀候选 "
                f"{sum(len(v) for v in candidates.values())} 条："
                f"`{repo.relative(target)}`"
            ),
        )
    return {
        "candidates": sum(len(items) for items in candidates.values()),
        "wrote": repo.relative(target),
        "pushed": publish["pushed"],
    }
