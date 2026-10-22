from __future__ import annotations

from datetime import UTC, datetime

from config import BotConfig
from github import gh_search_prs
from kb.config import KBConfig
from kb.sync import commit_paths, publish_commit
from kb.validate import validate_document
from notify import notify

TARGET = "inflight-prs.md"


def render(members: dict[str, list[dict]], now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    total = sum(len(items) for items in members.values())
    rows = []
    for login, pulls in members.items():
        if not pulls:
            rows.append(f"| @{login} | 0 | - | - |")
            continue
        for item in pulls:
            repo_name = item.get("repository", {}).get("nameWithOwner", "")
            draft = "draft" if item.get("isDraft") else "ready"
            rows.append(
                f"| @{login} | {item['number']} | "
                f"[{item['title']}]({item['url']}) | {repo_name} / {draft} |"
            )

    return f"""---
title: 在跟 PR 状态
date: {now.date().isoformat()}
author: team-kb-bot
status: active
---

# 在跟 PR 状态

## 目标

团队当前在跟的 open PR 总览（共 {total} 个，更新于
{now.isoformat(timespec="minutes")}）。

## 进展

| 成员 | PR | 标题 | 仓库 / 状态 |
|---|---|---|---|
{chr(10).join(rows) if rows else "| - | - | - | - |"}

## 风险与阻塞

- 请关注长期未更新的 PR 与 CI 失败项（数据来自 `gh search prs`）。

## 下一步

- 各成员确认自己的 PR 状态；阻塞项在周复盘提出。
"""


def run(config: BotConfig) -> dict:
    repo = KBConfig(config.repo)
    members = {login: gh_search_prs(login) for login in config.members}
    content = render(members)
    validate_document(repo, "worklog", content)

    target = repo.docs_dir / "work" / TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    commit = commit_paths(repo, [target], "work: refresh inflight PRs")
    publish = (
        publish_commit(repo, commit) if commit else {"pushed": True, "queued": False}
    )
    if publish["pushed"]:
        notify(config, "[team-kb] 在跟 PR 状态已刷新。")
    return {
        "wrote": repo.relative(target),
        "members": len(members),
        "prs": sum(len(items) for items in members.values()),
        "pushed": publish["pushed"],
    }
