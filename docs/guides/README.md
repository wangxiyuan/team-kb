# docs/guides — 学习与实践

团队的学习资料、踩坑记录、操作手册。按业务入口组织，文档类型由 frontmatter 的 `type` 标识。

## 允许的 type

| type | 用途 | 模板 |
|---|---|---|
| `guide` | 学习路径、架构拆解、概念说明 | `templates/guide.md` |
| `pitfall` | 踩坑记录：症状 → 根因 → 解法 | `templates/pitfall.md` |
| `recipe` | 操作手册：前置条件 → 步骤 → 验证 | `templates/recipe.md` |
| `note` | 未成熟的速记 | `templates/note.md` |

## 写入纪律

- 走 PR + 1 人评审（bot App 豁免）。
- 提交前先读对应模板，`propose_knowledge` 会校验。
- 每篇必须填写 `title / date / author / status / tags`。

## 示例

- `onboarding.md` — 新人第一周学习路径
- `scheduler-architecture.md` — vLLM scheduler 拆解
- `ascend-ima-pitfall.md` — Ascend kernel 非法内存访问踩坑
- `benchmark-recipe.md` — 如何跑吞吐/TTFT 压测

深度方法若可复用，应进一步沉淀到 `skills/`。