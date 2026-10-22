from __future__ import annotations

import json
from datetime import UTC, datetime

from .config import KBConfig


def _load(config: KBConfig) -> dict[str, dict]:
    if not config.usage_path.exists():
        return {}
    try:
        return json.loads(config.usage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(config: KBConfig, data: dict[str, dict]) -> None:
    config.usage_path.parent.mkdir(parents=True, exist_ok=True)
    config.usage_path.write_text(
        json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
    )


def record_use(config: KBConfig, name: str) -> dict:
    data = _load(config)
    entry = data.get(name, {"count": 0})
    entry["count"] = int(entry.get("count", 0)) + 1
    entry["last_used"] = datetime.now(UTC).isoformat(timespec="seconds")
    data[name] = entry
    _save(config, data)
    return entry


def usage_for(config: KBConfig, name: str) -> dict:
    return _load(config).get(name, {"count": 0})
