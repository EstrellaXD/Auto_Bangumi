# 3.3.4 Beta 与通用解析器历史整合设计

## 背景

`3.3.4-beta.1` 标签直接指向 PR #1074 的 head `86e39811`。当前
`3.3-dev` 的通用解析器工作则从共同基线 `31edfd84` 独立演进，并通过 merge
包含了两组 patch 等价但 SHA 不同的提交。直接合并两条分支会保留重复历史，
直接 rebase 当前 merge commit 又会重复重放相同补丁。

日历修复 `be8d23c3` 是 beta 标签的直接子提交，因此用它作为新集成基线。
只重放线性的 `refactor/generic-resource-tokenizer` 分支中
`31edfd84..bd04460b` 的 13 个提交。

## 方案比较

1. **直接 merge #1074 到现有 3.3-dev**：无需改写历史，但会保留重复 parser
   提交，且 migration/raw parser 冲突的语义不清晰。
2. **rebase 现有 3.3-dev**：该分支包含 merge commit 和两组 patch 等价提交，
   会重复应用相同改动。
3. **在 beta + 日历修复上重放线性 tokenizer 分支**：历史最小，能逐个解决三个
   实质冲突，并保留已发布 beta 的认证与 E2E 工作。采用此方案。

## 数据库迁移

已发布 beta 使用：

- v18：多用户字段与索引；
- v19：持久 session 与 API token；
- v20：scope-aware token 表重建。

旧 tokenizer 开发分支也曾把 v18 用作 Movie 表。最终历史必须保留 beta 的
v18-v20，不得改号或重跑 v20：v20 的 guard 故意恒为 false，重复执行会再次
重建 token 表。

新增迁移：

- v21：guarded 创建 Movie 表及索引；
- v22：guarded 修复多用户 v18 的三列与两个索引。

v22 用于已经运行过旧 `3.3-dev` 的数据库：它们的 `schema_version=18`，Movie
已存在，但用户表缺少 beta v18 字段。升级会依次运行 v19-v22，最终同时拥有
认证和 Movie schema。

## 冲突策略

- `raw_parser.py` 保留 selector-aware Classic/Preview 兼容入口；beta 的版本号、
  Movie 标题修复由新 tokenizer 及回归测试覆盖。
- OffsetScanner 保留 selector + `is_offset_signal`，同时保留 beta 的 #1072、CRC
  和 no-false-review 测试。
- Database facade 同时保留 `AuthDatabase`/`begin_write` 与 `MovieDatabase`。
- #1076 不再重放：beta 的 `af0c8833` 已用 `urlencode` 和多语言测试更完整地
  覆盖 TV/Movie search、去空格重试和 fallback。

## 验证与发布

必须覆盖三条真实升级谱系：

1. stable v17 -> v22；
2. `3.3.4-beta.1` auth v20 -> v22；
3. 旧 tokenizer Movie v18 -> v22。

每条路径验证 schema version、用户字段、auth/session/token 表及索引、Movie 表
与既有数据均保留。随后运行后端全量测试、Ruff、Black、Mypy，以及前端 Vitest、
类型检查、ESLint 和生产构建。最终用 `--force-with-lease` 更新 `3.3-dev`，并在
本地保留旧 `438aec67` 的备份 ref，防止并发远端更新或需要回滚。
