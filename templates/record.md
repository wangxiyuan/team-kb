---
schema_version: 1
type: record
required_fields: [time, task, area, result, potential_skill]
---

# record — 会话原料模板（仅说明，不直接复制）

`append_record` 按以下字段写入 `records/YYYY/MM/DD-<author>.md`：

| 字段 | 说明 |
|---|---|
| time | ISO8601 时间 |
| task | 任务简述 |
| area | 领域：kernel / scheduler / serving / ci / community / other |
| result | done / blocked / partial / failed |
| potential_skill | true / false，周复盘挖掘线索 |
| model | 可选，使用的模型 |
| content | 自由正文：上下文、做了什么、结论、踩坑 |

隐私规则：只写工作结果，禁止 prompt、聊天过程、个人上下文、密钥与个人信息。