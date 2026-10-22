from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

from .config import KBConfig
from .validate import split_document

SECTIONS = (
    ("skills", "skills"),
    ("guides", "docs/guides"),
    ("community", "docs/community"),
    ("work", "docs/work"),
)


def _last_commit_date(config: KBConfig, path: Path) -> date | None:
    completed = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", config.relative(path)],
        cwd=config.repo,
        capture_output=True,
        text=True,
        check=False,
    )
    value = completed.stdout.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def list_skills(config: KBConfig, tags: list[str] | None = None) -> list[dict]:
    from .usage import usage_for

    skills: list[dict] = []
    if not config.skills_dir.exists():
        return skills
    for path in sorted(config.skills_dir.glob("*/SKILL.md")):
        try:
            meta, _ = split_document(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        skill_tags = [str(tag) for tag in meta.get("tags") or []]
        if tags and not set(tags).intersection(skill_tags):
            continue
        last = _last_commit_date(config, path)
        stale = last is not None and (date.today() - last).days > 180
        usage = usage_for(config, meta.get("name", path.parent.name))
        skills.append(
            {
                "name": meta.get("name", path.parent.name),
                "description": meta.get("description", ""),
                "version": meta.get("version", ""),
                "owner": meta.get("owner", ""),
                "tags": skill_tags,
                "usage": usage.get("count", 0),
                "last_used": usage.get("last_used"),
                "stale": stale,
                "path": config.relative(path),
            }
        )
    return skills


def build_index(config: KBConfig) -> str:
    lines = [
        "# team-kb 索引",
        "",
        "> 本文件由 bot 自动生成，请勿手工编辑。",
        "",
        f"生成时间：{datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
    ]
    for title, relative in SECTIONS:
        lines.extend([f"## {title}", ""])
        base = config.repo / relative
        entries: list[str] = []
        if base.exists():
            for path in sorted(base.rglob("*.md")):
                if path.name.startswith("README"):
                    continue
                try:
                    meta, _ = split_document(path.read_text(encoding="utf-8"))
                except OSError:
                    continue
                label = meta.get("title") or meta.get("name") or path.parent.name
                entries.append(f"- [{label}]({config.relative(path)})")
        lines.extend(entries or ["（空）"])
        lines.append("")
    return "\n".join(lines)


def write_index(config: KBConfig) -> Path:
    config.index_path.write_text(build_index(config), encoding="utf-8")
    return config.index_path
