# docs/work — 工作清单与协调记忆

团队的工作计划、在跟 PR、会议纪要、技术决策（ADR）。

## 与 GitHub Issues 的边界

- **GitHub Issues / Projects**：执行跟踪（状态机、assignee、deadline）。
- **docs/work/**：协调记忆（背景、计划、结论、为什么这么做）。

## 允许的 type

| type | 用途 | 模板 |
|---|---|---|
| `worklog` | 迭代进展、在跟 PR 清单 | `templates/worklog.md` |
| `adr` | 团队技术决策 | `templates/adr.md` |
| `note` | 会议纪要等 | `templates/note.md` |

## 自动维护

- `bot/jobs/pr_status_sync.py` 每小时更新 `inflight-prs.md`（type: worklog）。
- `bot/jobs/aging_scan.py` 每周产出 `stale-skills-*.md`。

## 写入纪律

- 允许直推 main（高频、低门槛），每周复盘纠偏。
- 决策类（adr）建议即使直推也知会相关成员。