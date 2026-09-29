---
name: pax-execute
description: >
  在契约约束下执行，带审计和回滚。当 `plan.status == frozen` 且契约已确认，需要按计划实施时使用。
version: 0.1.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-execute

## Execution Contract
- 前置门禁：`contract` 已确认，`plan.status == frozen`
- 未通过门禁：拒绝启动，返回上游阶段
- 版本检查：`pax-ops/versions.json`
- 未通过内环验证不得标记完成
- 偏离契约必须暂停并重新协商
- fix 模式必须包含回归测试
- 禁止"顺手改别的"、禁止在根因判断有误时自行重新诊断

## 职责边界
- 做什么：在契约约束下执行，带审计和回滚
- 不做什么：不修改契约、不做独立评审、不做自诊断

## 输入
- 必需：`snapshot.plan`（`status: frozen`）、`snapshot.contract`
- 可选：`snapshot.diagnosis`（fix 模式必需）

## 工作流
1. 校验契约已确认，`plan.status == frozen`
2. 按计划步骤执行，每步执行前核对 `depends_on`
   - **数据订正步骤**：执行前检查目标仓库的 `script/` 目录结构，确认存储引擎与 plan 中标注的 `script_language` 一致。不一致则暂停并返回 plan 阶段重新确认。
3. 每步内环验证：做 → 验 → 修
4. 记录执行日志 `log[]` 与变更 `changes[]`
5. 检测偏差：若偏离契约，暂停并重新协商（写入 `deviations[]`）
6. 完成后触发 `pax-verify` 进行独立验证

执行模式：
- `mode: normal`：常规执行
- `mode: fix`：修复模式，必须针对已确认根因，必须包含回归测试

fix 模式额外约束：
- 修复必须针对已确认根因，不能"顺手改别的"
- 必须包含回归测试
- 必须验证修复不引入新问题
- 修复后重新运行 `pax-diagnose` 的最小复现案例
- 若发现根因判断有误，不允许自行重新诊断，必须返回 `pax-diagnose`

输出格式（示意）：

```yaml
execution:
  mode: normal | fix
  log:
    - { step: S<N>, action: "...", result: "...", timestamp: "..." }
  deviations:
    - { step: S<N>, deviation: "...", action: "..." }
  changes: [...]
```

## 输出契约
- `snapshot.execution`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 契约未确认 → 返回上游阶段
- `plan.status != frozen` → 返回规划阶段
- 内环验证失败 → 回滚并暂停
- 偏离契约 → 暂停，写入 `deviations[]`，重新协商
- 根因判断有误（fix 模式） → 返回诊断阶段

## 何时升级
- 需要独立验证 → `pax-verify`
- 计划无法执行 → 返回规划阶段
- 偏离超出容忍度 → `pax-council`
- 需要独立评审 → `pax-review`
