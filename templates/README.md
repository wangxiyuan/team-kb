# templates — 统一格式与校验标准

每个 `type` 对应一个模板文件，模板自身也是合法文档。`kb/validate.py` 读取模板的 frontmatter 得到校验规则：

```yaml
schema_version: 1
type: skill
required_frontmatter: [name, description, version, owner, tags]
required_sections: [触发场景, 方案, 验证方式]
```

- `required_frontmatter`：文档 frontmatter 必须包含的字段。
- `required_sections`：正文必须包含的 `##` 章节。
- `required_fields`：仅 `record` 使用，校验 `append_record` 的入参。
- `schema_version`：写入时校验版本一致；老文档不受新模板回溯约束。

| type | 用途 | 典型位置 |
|---|---|---|
| skill | 团队 SOP | `skills/<name>/SKILL.md` |
| guide | 学习/背景知识 | `docs/guides/` |
| pitfall | 踩坑记录 | `docs/guides/` |
| recipe | 操作手册 | `docs/guides/` |
| digest | 社区周报 | `docs/community/` |
| worklog | 工作清单/进展 | `docs/work/` |
| adr | 团队技术决策 | `docs/work/` |
| note | 其他速记 | 任意 docs 域 |
| record | 会话原料 | `records/` |

规则变更必须走 PR 评审，并同步修改对应模板与 `kb/validate.py`。