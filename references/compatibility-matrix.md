# Compatibility Matrix

来源：`pax-ops/versions.json` 的 `compatibility_matrix` 字段。
本文件只是人类可读镜像，权威源始终是 JSON。

| From | Can call |
|---|---|
| `pax-orchestrate@0.1` | `pax-clarify@0.1` |
| `pax-clarify@0.1` | `pax-diagnose@0.1`, `pax-plan@0.1` |
| `pax-diagnose@0.1` | `pax-plan@0.1` |
| `pax-plan@0.1` | `pax-execute@0.1` |
| `pax-execute@0.1` | `pax-review@0.1` |

## Breaking change 规则

- 修改 `pax-snapshot.schema.json` 中任一必填字段 → 家族 major bump
- 新增可选字段 → minor bump
- 新增 skill → minor bump
- 弃用 skill → minor bump（保留一个 minor 版本过渡期）
- 删除 skill → major bump
