# team-kb

10 人 vLLM 团队的中央知识总线：本地 clone + 远程集中 + bot 自治。

- 设计文档：[`DESIGN.md`](DESIGN.md)
- Agent 约定：[`AGENTS.md`](AGENTS.md)

## 快速开始（成员）

```bash
# 1. 克隆
git clone <org>/team-kb /path/to/team-kb
cd /path/to/team-kb

# 2. 初始化（检查 gh 身份、创建本地队列目录、安装 MCP server 依赖）
bash mcp-server/scripts/init.sh

# 3. 在 agent 中接入（见下，路径必须用绝对路径）
```

### opencode

`~/.config/opencode/opencode.jsonc`：

```jsonc
{
  "mcp": {
    "team-kb": {
      "type": "local",
      "command": [
        "uv", "run", "--project", "/path/to/team-kb/mcp-server",
        "python", "/path/to/team-kb/mcp-server/mcp_server.py",
        "--repo", "/path/to/team-kb"
      ],
      "enabled": true
    }
  }
}
```

### Claude Code

项目目录下 `.mcp.json`：

```json
{
  "mcpServers": {
    "team-kb": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/team-kb/mcp-server",
               "python", "/path/to/team-kb/mcp-server/mcp_server.py",
               "--repo", "/path/to/team-kb"]
    }
  }
}
```

### Cursor

Settings → MCP → 添加本地 server，命令同上。

## 目录

```
skills/     团队 SOP（检索使用，PR 合入）
docs/
  guides/   学习与实践（guide/pitfall/recipe）
  community/社区动态（digest）
  work/     工作清单（worklog/adr）
records/    会话原料矿（本人同意才记，1 个月归档）
templates/  统一格式与校验标准
mcp-server/ 成员 MCP server（FastMCP）
bot/        自治 bot（GitHub Actions cron）
```

## 仓库治理

GitHub Rulesets（路径级）：

- `skills/** docs/guides/** docs/community/** AGENTS.md templates/** mcp-server/**` → 需 PR + 1 评审；bot App 豁免
- `records/** docs/work/** INDEX.md` → 允许直推

## Bot 环境变量

在 GitHub Actions Secrets 中配置：

| 变量 | 说明 |
|---|---|
| `TEAM_KB_APP_ID` / `TEAM_KB_APP_PRIVATE_KEY` | GitHub App（`team-kb-bot`） |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` | OpenAI 兼容端点（自建 vLLM 或采购 API） |
| `OPENAI_MODEL` | 模型名，默认 `gpt-4o-mini` |
| `SLACK_WEBHOOK_URL` | Slack 通知 |

## 开发

```bash
cd mcp-server && uv sync && uv run pytest
cd bot && uv sync && uv run pytest
```