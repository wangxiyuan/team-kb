# team-kb 路由规则（全局）

本机已接入 team-kb MCP server（团队中央知识库）。以下规则适用于 vLLM 及团队相关任务；与工作无关的个人项目可忽略。

## 何时检索

- 开始非平凡任务前（调试、kernel、serving、CI、API 变更、方案设计），先调用 `team-kb_search_knowledge` 查 `skills` 和 `guides`。
- 需要发现有哪些 SOP：调用 `team-kb_list_skills`。
- 命中后必须用 `team-kb_read_document(path)` 读全文再执行，不要只看 snippet。
- **检索无结果 = 团队尚未沉淀**：不要换 query 反复重试，也不要用 `ls`/`find`/`grep` 扫描 team-kb 目录；继续正常排查，结束后可询问是否沉淀。
- **team-kb 仓库只能通过 MCP 工具读写**，不要用文件系统工具直接访问（会触发外部目录权限拦截）。

## 何时写入

- 只有用户明确同意才写 `records`；任务结束时可主动问"这次值得记录吗？"。
- 记录只写工作结果（task / area / result / content / potential_skill），**禁止** prompt、聊天过程、个人上下文、密钥、个人信息。
- 可复用方法或踩坑：用户要求沉淀时调用 `team-kb_propose_knowledge`（domain=skills|guides|community|work），自动开 PR。
- 写之前先 `team-kb_read_document("templates/<type>.md")`，按模板填写；校验失败会被拒写。

## 其他

- `team-kb_kb_status` 查看同步状态与待推队列；数据落后时调用 `team-kb_sync_knowledge`。
- `team-kb_append_record` / `team-kb_delete_record` 只允许在 `main` 分支。
- `propose_knowledge` 默认完成后切回 `main`，避免后续记录提交到 feature 分支。
- 完整团队规范：`team-kb_read_document("AGENTS.md")`。