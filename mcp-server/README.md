# mcp-server — 成员接口层

FastMCP 实现的 team-kb MCP server，通过 stdio 与本地 agent 通信。

## 启动

```bash
uv sync
uv run python mcp_server.py --repo ~/team-kb
```

通常由 agent 的 MCP client 自动拉起，无需手动启动。

## 模块

| 模块 | 职责 |
|---|---|
| `kb/config.py` | 仓库路径解析与 scope 映射 |
| `kb/search.py` | ripgrep 检索，按 scope/tags 过滤 |
| `kb/sync.py` | pull --rebase、commit、push、pending 队列 |
| `kb/validate.py` | 读取 `templates/` 并校验 frontmatter 与章节 |
| `kb/records.py` | append_record / delete_record（隐私优先） |
| `kb/propose.py` | 多文件 bundle 校验 + branch + PR |
| `kb/index.py` | INDEX.md 生成、skill 元数据与 stale 判定 |
| `kb/usage.py` | 本地 skill 使用计数（`.kb/usage.json`，不入库） |

## 测试

```bash
uv run pytest
```

## 环境变量

| 变量 | 说明 |
|---|---|
| `TEAM_KB_REPO` | 仓库路径（等效 `--repo`） |
| `TEAM_KB_NO_SYNC=1` | 禁用读前自动 pull（离线/调试） |