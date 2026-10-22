# team-kb — Agent 工作约定

本仓库是 10 人 vLLM 团队的中央知识总线。所有 agent（opencode / Claude Code / Cursor）在操作本仓库时必须遵守以下约定。

## 核心原则

1. **工具不限制，产物要集中**：成员可自由选择 agent、模型和 API；知识资产必须落到本仓库，由 git 管理。
2. **先检索，再动手**：面对非平凡任务，先调用 `search_knowledge` 查 `skills/` 和 `docs/`，命中则按既有 SOP 执行，不要重新发明。
3. **知识贡献可选**：解决非平凡问题后，建议沉淀一条 skill / pitfall / recipe，但不强制阻塞任务。

## 记录规则（隐私优先）

- **默认不记录任何会话。**
- agent 可以在会话结束时提示"这次值得记录吗？"，但**只有本人明确同意后才能调用 `append_record`**。
- 记录只写工作结果（任务、领域、结果、可沉淀线索），**禁止写入** prompt、聊天过程、个人上下文、密钥、凭证、个人信息。
- `records/` 为 append-only；本人可调用 `delete_record` 删除自己的条目。

## 写入路径纪律

| 路径 | 方式 |
|---|---|
| `records/**`、`docs/work/**`、`INDEX.md` | 直推 main |
| `skills/**`、`docs/guides/**`、`docs/community/**`、`templates/**`、`mcp-server/**`、`AGENTS.md` | 必须走 PR + 1 人评审 |

- 写入前先读 `team://templates/<type>`，按模板填写；校验失败会被拒写。
- 不得绕过校验、不得直接修改历史记录。

## 安全红线

- 不提交密钥、token、密码、内网凭证、个人隐私数据。
- 不修改本文件或 `templates/` 下的校验规则来规避约束；变更需 PR 评审。

## 周复盘

每周复盘扫描：
- `records/` 中 `potential_skill: true` 的线索
- `aging_scan` 产出的 stale 清单
- bot 周报（社区动态、PR 状态、新沉淀）

产出：新 skill / pitfall / recipe，或清理过期内容。