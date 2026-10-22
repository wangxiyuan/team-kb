# records — 会话原料矿（隐私优先）

记录"人 + agent 干了什么"的原始工作日志，是知识沉淀的**原料**，不是给人阅读的成品。

## 隐私规则（必须遵守）

- **默认不记录任何会话。**
- agent 可以询问"这次值得记录吗？"，**只有本人明确同意后才能写入**。
- 只记录工作结果：任务、领域、结果、可沉淀线索。
- **禁止写入**：prompt、聊天过程、个人上下文、密钥、凭证、个人信息。
- 本人可以删除自己的记录（`delete_record`）。

## 文件

```
records/YYYY/MM/DD-<author>-<HHMMSS>.md
records/archive/       # 超过 1 个月，由 bot 归档，默认不参与检索
```

每条记录一个文件，append-only，避免多人并发写入冲突。

## 字段

| 字段 | 说明 |
|---|---|
| `time` | ISO8601 |
| `task` | 任务简述 |
| `area` | kernel / scheduler / serving / ci / community / other |
| `result` | done / blocked / partial / failed |
| `potential_skill` | true 时进入周复盘挖掘候选 |
| `model` | 可选 |

## 用途

- 周复盘：查看团队在跟什么、卡在哪。
- `record_miner`：每周把 `potential_skill: true` 的条目提炼成沉淀候选（`docs/guides/sediment-candidates-*.md`）。
- `aging_scan`：每月把超过 1 个月的记录移入 `archive/`。