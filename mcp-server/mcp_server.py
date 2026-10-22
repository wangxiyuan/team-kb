from __future__ import annotations

import argparse
import contextlib
import os

from fastmcp import FastMCP
from kb.config import KBConfig, resolve_repo
from kb.index import list_skills as _list_skills
from kb.propose import propose_knowledge as _propose_knowledge
from kb.records import append_record as _append_record
from kb.records import current_author
from kb.records import delete_record as _delete_record
from kb.search import search
from kb.sync import ahead_behind, head, list_pending, remote_head, sync
from kb.usage import record_use
from kb.validate import ValidationError, split_document

mcp = FastMCP("team-kb")
_state: dict[str, KBConfig | None] = {"config": None}


def get_config() -> KBConfig:
    if _state["config"] is None:
        _state["config"] = resolve_repo()
    return _state["config"]  # type: ignore[return-value]


def _auto_pull() -> None:
    if os.environ.get("TEAM_KB_NO_SYNC") == "1":
        return
    with contextlib.suppress(Exception):
        sync(get_config(), pull_remote=True, push_pending=False)


def _error(exc: Exception) -> dict:
    if isinstance(exc, ValidationError):
        return {"error": exc.as_dict()}
    return {"error": {"code": type(exc).__name__, "detail": str(exc)}}


@mcp.tool()
def search_knowledge(
    query: str,
    scope: list[str] | None = None,
    tags: list[str] | None = None,
    top_k: int = 10,
) -> dict:
    """Search the team knowledge base (skills, guides, community, work, records)."""
    try:
        _auto_pull()
        return {"results": search(get_config(), query, scope, tags, top_k)}
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def read_document(path: str) -> dict:
    """Read a document from the knowledge base by repository-relative path."""
    try:
        _auto_pull()
        config = get_config()
        target = config.resolve_within_repo(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        content = target.read_text(encoding="utf-8")
        if target.name == "SKILL.md":
            meta, _ = split_document(content)
            record_use(config, meta.get("name", target.parent.name))
        return {"path": config.relative(target), "content": content}
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def list_skills(tags: list[str] | None = None) -> dict:
    """List available skills with metadata and staleness."""
    try:
        _auto_pull()
        return {"skills": _list_skills(get_config(), tags)}
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def kb_status() -> dict:
    """Report sync state, pending queue and bot health."""
    try:
        config = get_config()
        ahead, behind = ahead_behind(config)
        last_sync = None
        marker = config.repo / ".kb" / "last_sync"
        if marker.exists():
            last_sync = marker.read_text(encoding="utf-8").strip()
        bot_marker = config.repo / ".kb" / "bot_status.json"
        bot = (
            bot_marker.read_text(encoding="utf-8").strip()
            if bot_marker.exists()
            else None
        )
        return {
            "local_head": head(config),
            "remote_head": remote_head(config),
            "ahead": ahead,
            "behind": behind,
            "last_sync": last_sync,
            "pending": list_pending(config),
            "bot": bot,
        }
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def sync_knowledge(pull: bool = True, push_pending: bool = True) -> dict:
    """Pull remote knowledge and flush queued writes."""
    try:
        return sync(get_config(), pull_remote=pull, push_pending=push_pending)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def append_record(
    task: str,
    area: str,
    result: str,
    content: str,
    potential_skill: bool = False,
    model: str = "",
) -> dict:
    """Append a consented work record. Only call after the human agrees."""
    try:
        config = get_config()
        _auto_pull()
        return _append_record(
            config,
            task=task,
            area=area,
            result=result,
            content=content,
            potential_skill=potential_skill,
            model=model,
            author=current_author(config),
        )
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def delete_record(path: str) -> dict:
    """Delete one of your own records."""
    try:
        config = get_config()
        return _delete_record(config, path, author=current_author(config))
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def propose_knowledge(
    domain: str,
    type: str,
    name: str,
    files: list[dict],
) -> dict:
    """Validate and open a PR for a new skill or doc. files = [{path, content}]."""
    try:
        config = get_config()
        _auto_pull()
        return _propose_knowledge(
            config, domain=domain, doc_type=type, name=name, files=files
        )
    except Exception as exc:
        return _error(exc)


@mcp.resource("team://AGENTS.md")
def agents_md() -> str:
    return (get_config().repo / "AGENTS.md").read_text(encoding="utf-8")


@mcp.resource("team://skills/index")
def skills_index() -> str:
    skills = _list_skills(get_config())
    lines = ["# skills index", ""]
    for skill in skills:
        lines.append(f"- {skill['name']}: {skill['description']}")
    return "\n".join(lines)


@mcp.resource("team://templates/{doc_type}")
def template(doc_type: str) -> str:
    path = get_config().templates_dir / f"{doc_type}.md"
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="team-kb MCP server")
    parser.add_argument("--repo", help="path to the team-kb clone")
    args = parser.parse_args()
    _state["config"] = resolve_repo(args.repo)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
