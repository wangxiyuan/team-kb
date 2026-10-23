#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d .git ]; then
  echo "error: $REPO_ROOT is not a git repository" >&2
  exit 1
fi

command -v uv >/dev/null 2>&1 || { echo "error: uv is required (https://astral.sh/uv)" >&2; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "error: gh is required" >&2; exit 1; }
command -v rg >/dev/null 2>&1 || echo "warning: ripgrep (rg) not found; search will use a slower fallback"

if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
  echo "error: set your git identity first:" >&2
  echo "  git config user.name  <your-github-login>" >&2
  echo "  git config user.email <your-email>" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh is not authenticated; run: gh auth login" >&2
  exit 1
fi

mkdir -p "$REPO_ROOT/.kb/pending"
(cd "$REPO_ROOT/mcp-server" && uv sync --quiet)

cat <<EOF
team-kb initialized.

OpenCode (~/.config/opencode/opencode.jsonc):

  "instructions": ["$REPO_ROOT/ROUTER.md"],

  "mcp": {
    "team-kb": {
      "type": "local",
      "command": ["uv", "run", "--project", "$REPO_ROOT/mcp-server",
                  "python", "$REPO_ROOT/mcp-server/mcp_server.py",
                  "--repo", "$REPO_ROOT"],
      "enabled": true
    }
  }

The instructions entry is required: without it a fresh session sees the MCP
tools but not the team conventions (when to search, record, propose).

Then restart your agent. Try: "search the team knowledge base for <topic>".
EOF