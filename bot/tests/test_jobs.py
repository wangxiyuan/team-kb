from __future__ import annotations

from datetime import UTC, datetime, timedelta

from config import BotConfig
from jobs import community_sync, pr_status_sync, record_miner
from kb.config import KBConfig


def test_community_render_has_required_sections(bot_config: BotConfig) -> None:
    now = datetime(2026, 10, 22, tzinfo=UTC)
    content = community_sync.render(
        bot_config,
        releases=[
            {
                "name": "v1",
                "tag_name": "v1",
                "html_url": "u",
                "published_at": "2026-10-20T00:00:00Z",
            }
        ],
        pulls=[{"number": 1, "title": "fix", "html_url": "u"}],
        issues=[{"number": 2, "title": "bug", "html_url": "u"}],
        now=now,
    )
    assert "## 本周要点" in content
    assert "## 值得跟进的 PR/Issue" in content
    assert "week: 2026-W43" in content


def test_pr_status_render_lists_members(bot_config: BotConfig) -> None:
    now = datetime(2026, 10, 22, tzinfo=UTC)
    content = pr_status_sync.render(
        {
            "alice": [
                {
                    "number": 10,
                    "title": "t",
                    "url": "u",
                    "repository": {"nameWithOwner": "o/r"},
                    "isDraft": False,
                }
            ],
            "bob": [],
        },
        now=now,
    )
    assert "@alice" in content
    assert "@bob" in content
    assert "## 下一步" in content


def test_record_miner_collects_flagged_records(
    bot_config: BotConfig, kb: KBConfig
) -> None:
    now = datetime.now(UTC)
    record = kb.records_dir / "2026" / "10" / "22-alice-100000.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        f"""---
time: {now.isoformat()}
task: debug kernel
area: kernel
result: done
potential_skill: true
author: alice
---

root cause found
""",
        encoding="utf-8",
    )

    found = record_miner.collect(bot_config, now)

    assert list(found) == ["kernel"]
    assert found["kernel"][0]["task"] == "debug kernel"

    content = record_miner.render(bot_config, found, now)
    assert "## 正文" in content
    assert "debug kernel" in content


def test_record_miner_ignores_old_and_unflagged(
    bot_config: BotConfig, kb: KBConfig
) -> None:
    now = datetime.now(UTC)
    old = now - timedelta(days=90)
    path = kb.records_dir / "2026" / "07" / "old.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""---
time: {old.isoformat()}
task: old
area: kernel
result: done
potential_skill: true
---

old
""",
        encoding="utf-8",
    )

    assert record_miner.collect(bot_config, now) == {}
