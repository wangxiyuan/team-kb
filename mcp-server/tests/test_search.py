from __future__ import annotations

from kb.config import KBConfig
from kb.search import search


def test_search_finds_guides(kb_repo: KBConfig) -> None:
    path = kb_repo.docs_dir / "guides" / "attention.md"
    path.write_text("# attention\n\nflash attention is important\n", encoding="utf-8")

    results = search(kb_repo, "flash attention", scope=["guides"])

    assert results
    assert results[0]["path"] == "docs/guides/attention.md"


def test_search_respects_scope(kb_repo: KBConfig) -> None:
    path = kb_repo.docs_dir / "guides" / "attention.md"
    path.write_text("# attention\n\nflash attention\n", encoding="utf-8")

    assert search(kb_repo, "flash attention", scope=["work"]) == []


def test_search_filters_by_tags(kb_repo: KBConfig) -> None:
    path = kb_repo.docs_dir / "guides" / "tagged.md"
    path.write_text(
        "---\ntags: [kernel]\n---\n\n# tagged\n\nneedle\n", encoding="utf-8"
    )

    assert search(kb_repo, "needle", scope=["guides"], tags=["kernel"])
    assert search(kb_repo, "needle", scope=["guides"], tags=["serving"]) == []
