from __future__ import annotations

import re
from typing import Any

import yaml

from .config import KBConfig

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
KNOWN_TYPES = (
    "skill",
    "guide",
    "pitfall",
    "recipe",
    "digest",
    "worklog",
    "adr",
    "note",
    "record",
)


class ValidationError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


def split_document(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValidationError("FRONTMATTER_INVALID", "frontmatter must be a mapping")
    return meta, text[match.end() :]


def load_template(config: KBConfig, doc_type: str) -> dict[str, Any]:
    if doc_type not in KNOWN_TYPES:
        raise ValidationError("UNKNOWN_TYPE", f"unknown type: {doc_type}")
    path = config.templates_dir / f"{doc_type}.md"
    if not path.exists():
        raise ValidationError("TEMPLATE_MISSING", f"template not found: {path}")
    meta, _ = split_document(path.read_text(encoding="utf-8"))
    if meta.get("type") != doc_type:
        raise ValidationError(
            "TEMPLATE_INVALID",
            f"{path} declares type={meta.get('type')!r}, expected {doc_type!r}",
        )
    return meta


def validate_document(config: KBConfig, doc_type: str, text: str) -> dict[str, Any]:
    template = load_template(config, doc_type)
    meta, body = split_document(text)

    missing_fields = [
        field
        for field in template.get("required_frontmatter", [])
        if field not in meta or meta[field] in (None, "", [])
    ]
    if missing_fields:
        raise ValidationError(
            "FRONTMATTER_MISSING",
            f"missing frontmatter fields: {', '.join(missing_fields)}",
        )

    sections = set(SECTION_RE.findall(body))
    missing_sections = [
        section
        for section in template.get("required_sections", [])
        if section not in sections
    ]
    if missing_sections:
        raise ValidationError(
            "SCHEMA_MISSING_SECTION",
            f"missing sections: {', '.join(missing_sections)}",
        )

    return meta


def validate_record_fields(config: KBConfig, fields: dict[str, Any]) -> None:
    template = load_template(config, "record")
    missing = [
        field
        for field in template.get("required_fields", [])
        if field not in fields or fields[field] in (None, "")
    ]
    if missing:
        raise ValidationError(
            "RECORD_FIELD_MISSING", f"missing record fields: {', '.join(missing)}"
        )
