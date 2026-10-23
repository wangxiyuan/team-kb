from __future__ import annotations

import pytest
from kb.config import KBConfig
from kb.validate import ValidationError, validate_document, validate_record_fields

VALID_SKILL = """---
name: demo-skill
description: use when demoing
version: 1.0.0
owner: tester
tags: [demo]
usage: 0
last_used: ""
---

# demo

## 触发场景

demo

## 方案

demo

## 验证方式

demo
"""


def test_valid_skill_passes(kb_repo: KBConfig) -> None:
    meta = validate_document(kb_repo, "skill", VALID_SKILL)
    assert meta["name"] == "demo-skill"


def test_missing_section_rejected(kb_repo: KBConfig) -> None:
    broken = VALID_SKILL.replace("## 验证方式", "## 别的")
    with pytest.raises(ValidationError) as excinfo:
        validate_document(kb_repo, "skill", broken)
    assert excinfo.value.code == "SCHEMA_MISSING_SECTION"


def test_missing_frontmatter_rejected(kb_repo: KBConfig) -> None:
    broken = VALID_SKILL.replace("owner: tester\n", "")
    with pytest.raises(ValidationError) as excinfo:
        validate_document(kb_repo, "skill", broken)
    assert excinfo.value.code == "FRONTMATTER_MISSING"


def test_unknown_type_rejected(kb_repo: KBConfig) -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_document(kb_repo, "unknown", "---\n---\n")
    assert excinfo.value.code == "UNKNOWN_TYPE"


def test_type_mismatch_rejected(kb_repo: KBConfig) -> None:
    wrong = VALID_SKILL.replace("tags: [demo]", "tags: [demo]\ntype: pitfall")
    with pytest.raises(ValidationError) as excinfo:
        validate_document(kb_repo, "skill", wrong)
    assert excinfo.value.code == "TYPE_MISMATCH"


def test_record_fields_required(kb_repo: KBConfig) -> None:
    validate_record_fields(
        kb_repo,
        {
            "time": "now",
            "task": "t",
            "area": "kernel",
            "result": "done",
            "potential_skill": False,
        },
    )
    with pytest.raises(ValidationError) as excinfo:
        validate_record_fields(kb_repo, {"task": "t"})
    assert excinfo.value.code == "RECORD_FIELD_MISSING"
