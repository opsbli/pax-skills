# Compatibility Matrix

来源：`pax-ops/versions.json` 的 `compatibility_matrix` 字段。
本文件只是人类可读镜像，**权威源始终是 JSON**；两者不一致时以 JSON 为准，
并由 `pax-forge test` 的 `compatibility-matrix-consistency` 契约机械校验。

家族版本：`1.0.0`

## 层间允许的调用方向（全量）

`compatibility_matrix` 登记的是**层间**允许方向，与代码里的 `_allowed_calls()` 同源——
后者直接读取本矩阵，不再各自维护一份。层定义见 `schemas/pax-family.schema.yaml` 的 `layers`。

| From | Can call |
|---|---|
| `L0` | `L1`, `L4` |
| `L1` | `L1`, `L2`, `L3`, `L4` |
| `L2` | `L3`, `L4` |

未列出的方向一律非法，例如：

- `L4 → L1`（L4 是横切层，只能被调用，不主动下探）
- `L3 → *`（worker 是被委派方，不主动调用）
- `L2 → L2`、`L2 → L0`
- `meta → *`（`meta` 是 `non_runtime_layers`，不参与运行时）

## 主干 happy path（`main_flow`）

`main_flow` 只是给阅读者理解的典型执行链，**不构成额外约束**：

```
pax-orchestrate → pax-clarify → pax-diagnose → pax-plan → pax-execute → pax-review
```

`compatibility-matrix-consistency` 契约会校验这条链上每一步都落在矩阵允许的方向内。

## 为什么是「层」而不是「skill 对」

skill 级全量配对在 19 个 skill 下是 190+ 条，且每加一个 skill 都要重算，必然腐化。
层间登记是同一约束的等价、可维护形式：`layer-call-legality` 契约把每个 skill 的
frontmatter `layer` 与正文引用的目标 skill 层做交叉校验，等价于逐对检查。

**约定**：SKILL.md 正文里出现 `pax-<name>` 即被视为一条调用边。若只想表达「数据流向」
而非「调用」，写阶段名（如「回滚阶段」「评审阶段」）而不要写 skill 名，否则会被
`no-cycles` 契约计入调用图并可能与反向边构成假环。

## Breaking change 规则

- 修改 `snapshots/schema` 中任一必填字段 → 家族 major bump
- 新增可选字段 → minor bump
- 新增 skill → minor bump
- 弃用 skill → minor bump（保留一个 minor 版本过渡期）
- 删除 skill → major bump
- 新增/删除层间允许方向 → major bump（改变调用契约）
