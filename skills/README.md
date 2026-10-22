# skills — 团队标准作业程序（SOP）

存放"某类活儿该怎么做"的可复用方法论。agent 通过 `search_knowledge` 检索、`read_document` 读取后按步骤执行。

## 与 docs 的区别

- `docs/guides/` 是**学习与背景知识**（是什么、为什么）
- `skills/` 是**可执行的干活方法**（怎么做、怎么验证）

## 目录

```
skills/<name>/
  SKILL.md              # 必选
  agents/               # 可选：子 agent 指令
  scripts/              # 可选：配套脚本
  templates/            # 可选：输入模板
```

## SKILL.md 格式

```markdown
---
name: <kebab-case>
description: <触发条件，写清"何时使用">
version: 1.0.0
owner: <负责人>
tags: [kernel, debug]
---

## 触发场景
## 方案
## 验证方式
```

- 三段缺一不可，`propose_knowledge` 会校验拒写。
- `description` 决定 agent 能否命中，必须包含领域关键词与实际任务场景。

## 写入方式

通过 MCP `propose_knowledge(domain="skills", type="skill", name=..., files=[...])` 提交，自动开 PR，需 1 人评审。

## 生命周期

- `usage` 为本地使用计数（`.kb/usage.json`，不入仓）；超过 180 天未更新由 `aging_scan` 标记 stale。
- 被新 skill 取代时，在 PR 中标注 `superseded` 并说明替代者，不直接删除。