# docs/community — vLLM 社区动态

存放团队对 upstream 动态的**解读与消化**，不是转载原文。

## 产出方式

1. bot 每日通过 `community_sync` 抓取 `vllm-project/vllm` 的 release、合并 PR、活跃 issue，生成 `YYYY-Www.md` 草稿并合入。
2. 若配置了 `OPENAI_BASE_URL`，bot 会用 LLM 生成"本周要点"和"影响评估"。
3. 轮值者校对、补充团队观点；必要时关联到 `docs/work/` 的任务。

## 格式

`type: digest`，模板见 `templates/digest.md`，必填：

- frontmatter：`title / date / author / week / status`
- 章节：本周要点 / 值得跟进的 PR/Issue / 影响评估

## 写入纪律

- 成员：PR + 1 人评审。
- bot：自动合入（GitHub App 豁免规则）。
- 只记录影响评估与判断，不复述 changelog。