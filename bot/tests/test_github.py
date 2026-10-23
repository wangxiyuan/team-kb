from __future__ import annotations

import github


class _Result:
    returncode = 0
    stdout = "[]"
    stderr = ""


def test_gh_api_puts_params_in_query_string(monkeypatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return _Result()

    monkeypatch.setattr(github.subprocess, "run", fake_run)

    assert github.gh_api("repos/o/r/releases", {"per_page": "10"}) == []
    assert captured["args"] == ["gh", "api", "repos/o/r/releases?per_page=10"]
