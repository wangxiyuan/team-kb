# team-kb 设计文档（v1.0）

## 1. 背景与目标

10 人 vLLM 开发团队，成员各自使用不同的 agent（opencode / Claude Code / Cursor）与模型。三大诉求：

1. **工具不限制、产物要集中**：前端（agent / 模型 / API）自由发挥，后端知识资产统一进一个可评审、可回溯的 git 仓库。
2. **知识自成长**：不依赖员工自觉维护——全局 bot 定时抓取、同步、挖掘、清理。
3. **隐私可接受**：原始记录默认不记、本人同意才记，只记工作结果不记个人过程。

## 2. 总体架构

```
成员 agent (opencode/Claude Code/Cursor, 模型随意)
   │  MCP stdio
   ▼
本地 MCP server (mcp-server/, FastMCP)      GitHub Actions cron
   │   git 读写 (本人 gh/PAT)                    │  (bot, GitHub App)
   ▼                                            ▼
        ┌──────────────────────────────────────────┐
        │  team-kb 中心私有仓 (每人本地 clone)      │
        │  Rulesets 路径级守门 + rebase 同步引擎     │
        └───────────────┬──────────────────────────┘
                        ▼
                   Slack 通知 (周报/失败/合入)
```

- **写身份**：成员 = 本人本地 `gh`/PAT（审计即 git log）；bot = GitHub App（`team-kb-bot`）。
- **数据一致性**：读本地（离线可用）、写同步、冲突用 rebase 消化。

## 3. 仓库结构

```
team-kb/
  AGENTS.md                  # 团队共识/红线/沉淀规则，agent 启动自动加载
  mcp-server/                # 成员接口层
    pyproject.toml  mcp_server.py
    kb/  search.py sync.py records.py propose.py validate.py index.py config.py
    scripts/init.sh  tests/
  bot/                       # 自治层（复用 kb/ 核心模块）
    jobs/  community_sync.py pr_status_sync.py record_miner.py aging_scan.py
    digest_generator.py  runner.py  pyproject.toml  tests/
  skills/                    # SOP（仅搜索读取，PR 合入）
  docs/
    guides/    # 学习与实践：onboarding/架构拆解/pitfall/recipe
    community/ # 社区动态：upstream 解读/release 追踪/digest
    work/      # 工作清单：worklist/在跟 PR/会议纪要/adr
  records/                   # 原料矿（opt-in 写入，append-only）
    archive/                 # >1 个月归档，默认不参与检索
  templates/                 # 质检标准（type 即文件名）
  INDEX.md                   # bot 自动生成的检索索引
```

## 4. 四大内容区

### `skills/` — 标准作业程序

- 目录 `<name>/{SKILL.md, agents/, scripts/, templates/}`，多文件 bundle。
- frontmatter：`name / description(触发条件) / version / owner / tags`。
- 正文三段式：触发场景 / 方案 / 验证方式，缺段拒写。
- **仅搜索读取**：team-kb 是唯一源，不装本地、无副本漂移。agent 通过 `search_knowledge` 命中后 `read_document` 执行。
- PR + 1 评审；`usage` 由 MCP server 本地计数（`.kb/usage.json`，不入仓），`aging_scan` 依据最后一次 git 更新超过 180 天标 stale；被取代时标 `superseded`，不直接删。

### `docs/` — 业务导向三入口

`type` 是元数据（`guide / digest / worklog / adr / pitfall / recipe / note`），驱动模板与校验，不决定目录。

- `guides/`：学习与实践（onboarding、架构拆解、踩坑 pitfall、手册 recipe）——PR + 1。
- `community/`：upstream PR/issue 解读、release 追踪、竞品、每周 digest——PR + 1。
- `work/`：迭代 worklist、在跟 PR 清单、会议纪要、团队决策 adr——高频直推 main。

**边界**：GitHub Issues 负责执行跟踪（状态机/assignee/deadline）；`work/` 是协调记忆（计划/背景/结论）。

### `records/` — 原料矿（隐私优先）

- **写入仅凭本人明示**：agent 可提示"这条值得记录？"，人确认才写；默认零记录。
- **只记工作结果**：`task / area / result / learnings 线索 / model`，不含 prompt、聊天过程、个人上下文。
- **身份 = GitHub 身份**：与 PR/commit 同级透明度；本人有 `delete_record` 权。
- 每条记录一个文件：`records/YYYY/MM/DD-<author>-<HHMMSS>.md`；append-only；**1 个月归档**到 `records/archive/`，默认不参与检索。

### `templates/` — 质检标准

- 顶层唯一；`type` 即文件名（`skill / digest / worklog / adr / pitfall / recipe / guide / note / record`）。
- `kb/validate.py` 解析模板 frontmatter 得到必填字段与章节，写入时强制校验，缺段拒写。
- MCP 暴露 `team://templates/<type>` 供 agent 写前参照；带 `schema_version`，仅在写入时生效，老文档不受新模板约束。

## 5. MCP API

| 工具 | 入参 | 返回 | 权限 |
|---|---|---|---|
| `search_knowledge` | `query, scope=[skills,guides,community,work], tags, top_k`（records 需显式指定） | `[{path,snippet,heading}]` + hint | 读 |
| `read_document` | `path` | `{path,content}`（读 SKILL.md 时 usage+1） | 读 |
| `list_skills` | `tags?` | `[{name,description,version,owner,usage,stale}]` | 读 |
| `kb_status` | — | `{local_head,remote_head,ahead,behind,last_sync,pending,bot}` | 读 |
| `sync_knowledge` | `pull=true,push_pending=true` | `{pulled,pushed,conflicts}` | 读+写 |
| `append_record` | `task,area,result,content,potential_skill,model?` | `{record_path,commit}` 直推 main | 写(本人) |
| `delete_record` | `path` | `{deleted}`（仅本人条目） | 写(本人) |
| `propose_knowledge` | `domain,type,name,files[]`, `base_branch=main, return_to_base=true` | `{pr_url,branch,returned_to}` 自动开 PR | 写(PR) |

> 创建 PR 后默认切回 `base_branch`，避免后续 `append_record` 误提交到 feature 分支；`records` 只允许在 `main` 写入，否则拒绝并提示。

资源：`team://AGENTS.md`、`team://skills/index`、`team://templates/<type>`。

### 5.1 渐进式披露（Agent 侧）

新会话默认只知道工具名和描述，不知道团队约定。因此分四层注入：

| 层 | 内容 | 载体 | 何时进入上下文 |
|---|---|---|---|
| L0 路由 | 何时检索/写入/读模板，约 15 行 | `ROUTER.md`，通过 opencode `instructions` 注入 | 每个会话始终 |
| L1 工具 | 8 个工具的触发条件 | MCP tool docstring（opencode 自动展示） | 每个会话始终 |
| L2 索引 | 有哪些 skill、检索入口 | `list_skills` / `search_knowledge` | agent 主动调用 |
| L3 全文 | 具体 SOP / 指南 | `read_document(path)` | 命中后调用 |
| L4 模板 | 写入前的格式约束 | `read_document("templates/<type>.md")` | 写之前调用 |

注意：opencode 不会把 MCP resources 自动注入上下文，所以路由必须靠 `instructions` 文件，模板必须靠 `read_document`，不能依赖 `team://` 资源。MCP 工具本身也占上下文，当前 8 个是合理规模，新增工具需谨慎。

## 6. 同步引擎

- 读前 `git pull --rebase --autostash`（文件锁防并发）→ 本地检索；远端不可达时读照常。
- `append_record` 写后立即 push；冲突 rebase 重试 → 失败进本地 `.kb/pending/` 队列 → 下次 `sync_knowledge` 重推并回报 agent。
- `propose_knowledge` 本地 branch → commit → `push --force-with-lease`（仅 feature 分支）→ `gh pr create`。

## 7. 自治 bot（GitHub Actions cron，全部自动）

| 任务 | 频率 | 产出 | 去向 |
|---|---|---|---|
| `community_sync` | 每日 | digest（GitHub API 抓取 + LLM 总结） | `docs/community/` 自动合入 |
| `pr_status_sync` | 每小时 | 团队在跟 PR 的 CI/状态 | `docs/work/` 直推 |
| `record_miner` | 每周 | 由已同意记录提炼 skill/pitfall 候选 | 自动合入 |
| `aging_scan` | 每周 | stale 标记 + records>1 月归档 | 直推 |

- LLM：`OPENAI_BASE_URL` / `OPENAI_API_KEY` 配置化（自建 vLLM 或采购均可）。
- 通知：Slack（周报/失败/合入）；健康心跳 = 任务失败即告警。
- **安全网**：bot 全部产出过 `validate.py` 校验 → git 全量可回滚 → `aging_scan` 可清理 → Slack 全程可见。

## 8. 权限与治理（GitHub Rulesets，路径级）

- `skills/** docs/guides/** docs/community/** AGENTS.md templates/** mcp-server/**` → 需 PR + 1（成员）；**bot App 豁免**。
- `records/** docs/work/** INDEX.md` → 允许直推（成员 + bot）。

## 9. 运营节奏

周复盘：扫 `records` 的 `potential_skill` 线索 + `aging_scan` stale 清单 + bot 周报，产出更新与清理。AGENTS.md 固化规则：agent 可建议记录但写入需人确认；解决非平凡问题 = 交付可含一条知识贡献。

## 10. 里程碑

| 阶段 | 内容 | 周期 |
|---|---|---|
| P1 | 仓库骨架 + 读工具 + 同步引擎 + init.sh + 1 人 pilot | 1 周 |
| P2 | 写工具 + PR + Rulesets + templates + 10 人接入 | 1 周 |
| P3 | bot 层：Actions + 4 jobs + Slack + App 豁免 | 1-2 周 |
| P4 | 周复盘飞轮 + 度量 + 可选语义检索 | 持续 |

---

# 附录：用户视角的使用方式

## 场景 A：成员普通一天（检索 → 干活 → 沉淀）

1. **打开 agent**。MCP client 连上本地 server，server 启动时挂载 `team://AGENTS.md`（团队红线、沉淀规则）与 `team://skills/index`，并自动 `git pull --rebase` 同步最新知识。
2. **遇到问题**。agent 调 `search_knowledge(query="ascend IMA 调试", scope=["skills","guides"])` → 本地 ripgrep 命中 `skills/ascend-ima-debug/SKILL.md` → `read_document` 读取（usage+1）→ 按三段式步骤执行；命中 pitfall 则直接引用结论。
3. **调通问题**。agent 按 AGENTS.md 提示"这次值得记录吗？"。人确认后调 `append_record(...)` → 写入 `records/2026/10/DD-22-<github>-<HHMMSS>.md` → commit + push 到中心仓（原料入矿）。
4. **沉淀方法**。调 `propose_knowledge(domain="skills", type="skill", name="...", files=[...])` → 本地 branch → push → `gh pr create` → 同事评审合入。
5. **涉及**：`AGENTS.md`、`INDEX.md`、`skills/*/SKILL.md`、`docs/guides/*`、`records/YYYY/MM/DD-<author>-<HHMMSS>.md`、GitHub PR。

## 场景 B：轮值者做社区动态

- agent 命中 `skills/community-digest` 按步骤执行；bot 已生成 `docs/community/YYYY-Www.md` 草稿并 Slack 通知。
- 轮值者校对、补团队观点、确认合入。

## 场景 C：bot 无人值守

- `community_sync`：抓 upstream → LLM 总结 → 写 `docs/community/` → 自动合入 → Slack。
- `pr_status_sync`：拉团队 PR 状态 → 更新 `docs/work/` → 直推。
- `record_miner`：扫 `potential_skill: true` → 提炼候选 → 校验 → 自动合入 → Slack。
- `aging_scan`：`records` >1 月归档 + 闲置 skill 标 stale。

## 场景 D：数据流全景

```
                        ┌── 检索: agent ──MCP──► search.py ──ripgrep──► skills/ docs/ records/
  [成员动作]             ├── 记录: agent ──MCP──► records.py ──git push──► records/ (直推 main)
    agent 干活            └── 沉淀: agent ──MCP──► propose.py ──branch+PR──► skills/ docs/ (评审合入)
                                                                    │
                        ┌── 抓取: Actions ──GitHub API──► community_sync ──► docs/community/ (自动合入)
  [bot 自治]             ├── 同步: Actions ──► pr_status_sync ──► docs/work/ (直推)
    cron 定时             ├── 挖掘: Actions ──► record_miner ──► skills/ docs/ (自动合入)
                          └── 清理: Actions ──► aging_scan ──► records/archive/ + stale
                                                                │
                        ┌── 唯一源: templates/ ◄── validate.py 校验每一次写入
                        └── 可见性: Slack 通知 / kb_status / git log 审计
```

## 一句话

> 你照常用你的 agent、你的模型、你的习惯干活；凡是**搜**知识、**存**经验、**写**方案的动作，都自动落到 `team-kb` 这一个中心仓库里；bot 负责让这个仓库永远活着，你只需在觉得值得时点一下"记录"。