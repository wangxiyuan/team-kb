# bot — 自治层

GitHub Actions cron 定时执行的知识库维护任务。复用 `mcp-server/kb/` 的核心模块，以 `team-kb-bot` 身份提交。

## 任务

| 任务 | 频率 | 产出 |
|---|---|---|
| `community_sync` | 每日 | `docs/community/<week>.md` |
| `pr_status_sync` | 每小时 | `docs/work/inflight-prs.md` |
| `record_miner` | 每周 | `docs/guides/sediment-candidates-<week>.md` |
| `aging_scan` | 每周 | `records/archive/`、`docs/work/stale-skills-<week>.md`、`INDEX.md` |

## 本地运行

```bash
uv sync
TEAM_KB_REPO=~/team-kb uv run python runner.py community_sync
```

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| `TEAM_KB_REPO` | 是 | 仓库路径 |
| `TEAM_KB_UPSTREAM` | 否 | upstream 仓库，默认 `vllm-project/vllm` |
| `TEAM_KB_MEMBERS` | 否 | 逗号分隔的 GitHub 成员列表 |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` | 否 | OpenAI 兼容端点；未配置则跳过 LLM 总结 |
| `SLACK_WEBHOOK_URL` | 否 | Slack 通知 |

## 安全网

- 所有产出先过 `kb/validate.py` 校验
- 全部为 git 提交，可回滚
- `aging_scan` 每周清理过期内容
- Slack 通知与 `.kb/bot_status.json` 提供可见性