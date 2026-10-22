---
time: '2026-10-22T16:50:30-07:00'
task: 走读 vLLM v1 KV cache 代码并产出知识文章
area: scheduler
result: done
potential_skill: true
model: deepseek-v4.1-flash-1017
author: wangxiyuan
---

走读 vLLM v1 KV cache 相关代码（KVCacheManager、BlockPool、block hash 链、前缀缓存、抢占与回收），按 guide 模板产出《vLLM v1 KV Cache 走读》，通过 MCP propose_knowledge 提交为 PR #1。

过程中发现并修复了 3 个流程问题：
1) propose_knowledge 创建 PR 后本地停留在 feature 分支，后续 append_record 会误提交到该分支；改为默认 return_to_base，并在 records 侧增加仅 main 可写的守卫。
2) validate_document 未校验文档 type，增加 TYPE_MISMATCH。
3) bot 的 gh api 用 -f 传参被当成 POST 导致 422，改为 query string。

可沉淀方向：团队「用 MCP 走读代码并产出知识文章」的标准流程（检索→模板→propose→PR→合并后验证）。
