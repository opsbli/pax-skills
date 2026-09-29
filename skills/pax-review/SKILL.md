---
name: pax-review
description: >
  独立评审门禁，对照成功标准决定通过/拒绝。当 `pax-execute` 完成执行，需要独立判定成功/失败/升级时使用。
version: 0.1.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-review

## Execution Contract
- 前置门禁：`snapshot.execution` 已产出，`plan.verification_strategy[]` 存在
- 未通过门禁：拒绝启动，返回执行阶段补齐日志
- 版本检查：`pax-ops/versions.json`
- 门禁：`verdict: pass` 才能进入文档沉淀阶段
- 门禁：`verdict: fail` 返回执行阶段
- 门禁：`verdict: escalated` 升级 `pax-council`
- 禁止在缺乏 `pax-verify` 印章时给出 `verdict: pass`

## 职责边界
- 做什么：独立评审门禁，对照成功标准决定通过/拒绝
- 不做什么：不修改执行结果、不重跑执行、不写文档

## 输入
- 必需：`snapshot.execution`、`snapshot.plan`、`snapshot.contract`
- 可选：`snapshot.verify_stamp`

## 工作流
1. 读取执行结果与成功标准（`plan.verification_strategy`）
2. 对照标准逐项验收，记录每项 `pass/fail`
3. 检查偏差是否已处理（`execution.deviations[]`）
4. 检查 `pax-verify` 印章
5. 产出评审结论与印章

**五态 verdict**：

| verdict | 语义 | 后续 |
|---|---|---|
| `pass` | 全部通过 | 进入文档沉淀 |
| `fail` | 存在未通过项 | 返回执行阶段 |
| `partial` | 部分通过，允许延期 | 记录待办，进入文档草稿 |
| `blocked` | 证据或印章缺失 | 返回执行/验证阶段 |
| `escalated` | 超出评审权限 | 升级 `pax-council` |

输出格式（示意）：

```yaml
review:
  verdict: pass | fail | partial | blocked | escalated
  stamp: "<唯一标识>"
  rationale: "..."
  findings: [...]
```

## 输出契约
- `snapshot.review`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- `pax-verify` 印章缺失 → `verdict: blocked`
- 与契约偏差未处理 → `verdict: fail`
- 超出评审权限 → `verdict: escalated`

## 何时升级
- `verdict: pass` → 进入文档沉淀阶段
- `verdict: fail` → 返回执行阶段
- `verdict: escalated` → `pax-council`
- 需要独立验证 → `pax-verify`
