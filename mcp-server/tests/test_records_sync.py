from __future__ import annotations

from kb.config import KBConfig
from kb.records import append_record, delete_record
from kb.sync import commit_paths, publish_commit


def test_commit_and_push(kb_repo_with_origin: KBConfig) -> None:
    path = kb_repo_with_origin.docs_dir / "guides" / "note.md"
    path.write_text("# note\n", encoding="utf-8")

    commit = commit_paths(kb_repo_with_origin, [path], "add note")
    assert commit

    result = publish_commit(kb_repo_with_origin, commit)
    assert result["pushed"] is True
    assert result["queued"] is False


def test_append_record_creates_file(kb_repo: KBConfig) -> None:
    result = append_record(
        kb_repo,
        task="debug kernel",
        area="kernel",
        result="done",
        content="root cause found",
        potential_skill=True,
    )

    record_path = kb_repo.repo / result["record_path"]
    assert record_path.exists()
    assert "potential_skill: true" in record_path.read_text(encoding="utf-8")
    assert result["queued"] is True


def test_delete_record_requires_owner(kb_repo: KBConfig) -> None:
    result = append_record(
        kb_repo,
        task="debug",
        area="kernel",
        result="done",
        content="body",
        author="tester",
    )

    deleted = delete_record(kb_repo, result["record_path"], author="tester")
    assert deleted["deleted"] == result["record_path"]
    assert not (kb_repo.repo / result["record_path"]).exists()
