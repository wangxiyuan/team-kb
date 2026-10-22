from __future__ import annotations

import subprocess
from datetime import datetime

import yaml

from .config import KBConfig
from .sync import commit_paths, publish_commit
from .validate import validate_record_fields


def current_author(config: KBConfig) -> str:
    completed = subprocess.run(
        ["git", "config", "user.name"],
        cwd=config.repo,
        capture_output=True,
        text=True,
        check=False,
    )
    name = completed.stdout.strip()
    if not name:
        raise RuntimeError(
            "git user.name is not configured; run: git config user.name <you>"
        )
    return "-".join(name.split()).lower()


def append_record(
    config: KBConfig,
    task: str,
    area: str,
    result: str,
    content: str,
    potential_skill: bool = False,
    model: str = "",
    author: str | None = None,
) -> dict:
    now = datetime.now().astimezone()
    fields = {
        "time": now.isoformat(timespec="seconds"),
        "task": task,
        "area": area,
        "result": result,
        "potential_skill": bool(potential_skill),
        "model": model,
    }
    validate_record_fields(config, fields)
    author = author or current_author(config)

    date_dir = config.records_dir / now.strftime("%Y/%m")
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / f"{now.strftime('%d')}-{author}-{now.strftime('%H%M%S')}.md"

    frontmatter = yaml.safe_dump(
        {
            "time": fields["time"],
            "task": task,
            "area": area,
            "result": result,
            "potential_skill": bool(potential_skill),
            "model": model or None,
            "author": author,
        },
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    path.write_text(f"---\n{frontmatter}\n---\n\n{content.strip()}\n", encoding="utf-8")

    commit = commit_paths(config, [path], f"record: {task}")
    publish = (
        publish_commit(config, commit) if commit else {"pushed": True, "queued": False}
    )
    return {
        "record_path": config.relative(path),
        "commit": commit,
        "pushed": publish["pushed"],
        "queued": publish["queued"],
    }


def delete_record(
    config: KBConfig, relative_path: str, author: str | None = None
) -> dict:
    from .validate import split_document

    path = config.resolve_within_repo(relative_path)
    if config.records_dir.resolve() not in path.parents:
        raise ValueError("not a records file")
    if not path.exists():
        raise FileNotFoundError(relative_path)

    meta, _ = split_document(path.read_text(encoding="utf-8"))
    owner = str(meta.get("author", ""))
    if author and owner != author:
        raise PermissionError("can only delete your own record")

    path.unlink()
    commit = commit_paths(config, [path], f"record: delete {relative_path}")
    publish = (
        publish_commit(config, commit) if commit else {"pushed": True, "queued": False}
    )
    return {"deleted": relative_path, "commit": commit, "queued": publish["queued"]}
