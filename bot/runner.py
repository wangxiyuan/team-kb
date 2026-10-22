from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BOT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BOT_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))
sys.path.insert(0, str(BOT_ROOT))

from config import load  # noqa: E402
from jobs import aging_scan, community_sync, pr_status_sync, record_miner  # noqa: E402

JOBS = {
    "community_sync": community_sync.run,
    "pr_status_sync": pr_status_sync.run,
    "record_miner": record_miner.run,
    "aging_scan": aging_scan.run,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in JOBS:
        print(f"usage: runner.py <{'|'.join(JOBS)}>", file=sys.stderr)
        raise SystemExit(2)

    config = load()
    name = sys.argv[1]
    result = JOBS[name](config)

    status_path = config.repo / ".kb" / "bot_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "job": name,
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                "result": result,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
