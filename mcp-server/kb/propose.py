from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from .config import KBConfig
from .sync import git
from .validate import ValidationError, validate_document

DOC_DOMAINS = ("guides", "community", "work")


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip()).strip("-").lower()
    if not slug:
        raise ValidationError("NAME_INVALID", f"invalid name: {name!r}")
    return slug


def _target_files(
    config: KBConfig, domain: str, doc_type: str, name: str, files: list[dict]
) -> list[tuple[Path, str]]:
    if not files:
        raise ValidationError("FILES_EMPTY", "files must not be empty")

    if domain == "skills":
        if doc_type != "skill":
            raise ValidationError(
                "DOMAIN_TYPE_MISMATCH", "skills domain requires type=skill"
            )
        first = Path(files[0]["path"]).name
        if first != "SKILL.md":
            raise ValidationError(
                "FILES_INVALID", "first file for a skill must be SKILL.md"
            )
        root = config.skills_dir / _slug(name)
        return [(root / entry["path"], entry["content"]) for entry in files]

    if domain not in DOC_DOMAINS:
        raise ValidationError("DOMAIN_INVALID", f"unknown domain: {domain}")

    if len(files) != 1:
        raise ValidationError("FILES_INVALID", "docs require exactly one markdown file")
    relative = Path(files[0]["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError("FILES_INVALID", "file path must be repository-relative")
    filename = relative.name if relative.suffix == ".md" else f"{_slug(name)}.md"
    return [(config.docs_dir / domain / filename, files[0]["content"])]


def propose_knowledge(
    config: KBConfig,
    domain: str,
    doc_type: str,
    name: str,
    files: list[dict],
    base_branch: str = "main",
    return_to_base: bool = True,
) -> dict:
    targets = _target_files(config, domain, doc_type, name, files)

    for path, content in targets:
        if path.suffix == ".md":
            validate_document(config, doc_type, content)

    branch = f"kb/{doc_type}/{_slug(name)}-{int(time.time())}"
    git(config, "checkout", base_branch)
    git(config, "pull", "--rebase", "--autostash", check=False)
    git(config, "checkout", "-b", branch)

    for path, content in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    relatives = [config.relative(path) for path, _ in targets]
    git(config, "add", "--", *relatives)
    git(config, "commit", "-m", f"{doc_type}: add {name}")
    push = git(
        config, "push", "--force-with-lease", "-u", "origin", branch, check=False
    )
    if push.returncode != 0:
        raise RuntimeError(push.stderr.strip() or "git push failed")

    title = f"{doc_type}: add {name}"
    body = "Created by team-kb MCP server.\n\nPaths:\n" + "\n".join(
        f"- `{relative}`" for relative in relatives
    )
    completed = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base_branch,
            "--head",
            branch,
        ],
        cwd=config.repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "gh pr create failed")

    returned_to = None
    if return_to_base:
        checkout = git(config, "checkout", base_branch, check=False)
        if checkout.returncode == 0:
            returned_to = base_branch

    return {
        "pr_url": completed.stdout.strip().splitlines()[-1],
        "branch": branch,
        "returned_to": returned_to,
    }
