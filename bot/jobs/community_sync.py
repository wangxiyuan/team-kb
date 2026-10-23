from __future__ import annotations

from datetime import UTC, datetime, timedelta

from config import BotConfig
from digest_generator import summarize
from github import gh_api
from kb.config import KBConfig
from kb.sync import commit_paths, publish_commit
from kb.validate import validate_document
from notify import notify

WINDOW_DAYS = 7


def _week_label(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _recent_releases(upstream: str, since: datetime) -> list[dict]:
    releases = gh_api(f"repos/{upstream}/releases", {"per_page": "10"})
    recent = []
    for item in releases:
        published = item.get("published_at")
        if not published:
            continue
        if datetime.fromisoformat(published.replace("Z", "+00:00")) >= since:
            recent.append(item)
    return recent


def _recent_prs(upstream: str, since: datetime) -> list[dict]:
    pulls = gh_api(
        f"repos/{upstream}/pulls",
        {"state": "closed", "sort": "updated", "direction": "desc", "per_page": "50"},
    )
    merged = []
    for item in pulls:
        if not item.get("merged_at"):
            continue
        if datetime.fromisoformat(item["merged_at"].replace("Z", "+00:00")) >= since:
            merged.append(item)
    return merged


def _recent_issues(upstream: str, since: datetime) -> list[dict]:
    issues = gh_api(
        f"repos/{upstream}/issues",
        {"state": "all", "sort": "updated", "direction": "desc", "per_page": "50"},
    )
    return [
        item
        for item in issues
        if "pull_request" not in item
        and datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")) >= since
    ]


def render(
    config: BotConfig,
    releases: list[dict],
    pulls: list[dict],
    issues: list[dict],
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(UTC)
    week = _week_label(now)
    release_lines = [
        (
            f"- [{item['name'] or item['tag_name']}]({item['html_url']})"
            f" — {item['published_at'][:10]}"
        )
        for item in releases
    ] or ["- 无"]
    pr_lines = [
        f"- #{item['number']} {item['title']} ([link]({item['html_url']}))"
        for item in pulls[:15]
    ] or ["- 无"]
    issue_lines = [
        f"- #{item['number']} {item['title']} ([link]({item['html_url']}))"
        for item in issues[:15]
    ] or ["- 无"]

    raw = (
        "Releases:\n"
        + "\n".join(release_lines)
        + "\n\nMerged PRs:\n"
        + "\n".join(pr_lines)
        + "\n\nActive issues:\n"
        + "\n".join(issue_lines)
    )
    summary = summarize(
        config,
        (
            "Summarize this week's vLLM community activity in Chinese, "
            f"5 bullets max:\n{raw}"
        ),
        system="You are a concise engineering analyst for a vLLM development team.",
    )
    impact = summarize(
        config,
        f"List at most 5 items the vLLM team should follow up on, in Chinese:\n{raw}",
        system="You are a vLLM technical lead. Be specific and actionable.",
    )

    return f"""---
title: vLLM 社区动态 {week}
date: {now.date().isoformat()}
author: team-kb-bot
week: {week}
status: active
---

# vLLM 社区动态 {week}

## 本周要点

{summary or "- 待补充（未配置 LLM）"}

## 值得跟进的 PR/Issue

{chr(10).join(pr_lines + issue_lines)}

## 影响评估

{impact or "- 待团队补充"}
"""


def run(config: BotConfig) -> dict:
    repo = KBConfig(config.repo)
    now = datetime.now(UTC)
    since = now - timedelta(days=WINDOW_DAYS)

    releases = _recent_releases(config.upstream, since)
    pulls = _recent_prs(config.upstream, since)
    issues = _recent_issues(config.upstream, since)
    content = render(config, releases, pulls, issues, now)
    validate_document(repo, "digest", content)

    target = repo.docs_dir / "community" / f"{_week_label(now)}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    commit = commit_paths(repo, [target], f"community: digest {_week_label(now)}")
    publish = (
        publish_commit(repo, commit) if commit else {"pushed": True, "queued": False}
    )
    notify(
        config,
        (
            f"[team-kb] 社区动态 {_week_label(now)} 已生成并合入："
            f"`{repo.relative(target)}`"
        ),
    )
    return {
        "wrote": repo.relative(target),
        "releases": len(releases),
        "pulls": len(pulls),
        "issues": len(issues),
        "pushed": publish["pushed"],
    }
