---
name: pax-plan
description: >
  将已澄清/诊断的目标转化为机器可冻结的任务计划。当共识收敛且门禁通过，需要产出可执行、可回滚的 `plan` 区时使用。
version: 0.1.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-plan

## Execution Contract
- 前置门禁：`consensus.gaps_remaining == []`；诊断类任务额外要求 `diagnosis.status == settled` 且 `diagnosis.root_cause.confidence >= medium`
- 未通过门禁：拒绝冻结，返回澄清或诊断阶段
- 版本检查：`pax-ops/versions.json`
- 禁止在门禁不通过时冻结计划
- 计划冻结后（`plan.status == frozen`）不得就地修改，需重新协商

## 职责边界
- 做什么：将已澄清/诊断的目标转化为机器可冻结的任务计划
- 不做什么：不执行动作、不做共识收敛、不做独立评审

## 输入
- 必需：`snapshot.consensus`
- 可选：`snapshot.diagnosis`（诊断类任务必需）、`snapshot.contract`

## 工作流
1. 读取快照，校验前置门禁
2. 分解目标为步骤，每步绑定证据（`evidence[]`）
   - **数据订正步骤**：必须包含前置检查 `prerequisite: storage_backend_confirmed`，`script_language` 必须与诊断阶段 D2 确认的 `infrastructure.script_language` 一致。不一致则拒绝冻结。
   - **跨仓库步骤**：标注 `repo: <仓库名>` 和 `execution_strategy: <subagent|separate_session|manual_handoff>`。不标注则拒绝冻结。
3. 标注依赖（`depends_on`）、风险、回退点（`rollback`）
4. 定义验证策略 `verification_strategy[]`（步骤 → 方法 → 通过标准）
5. 写入快照 `plan` 区，状态置 `frozen`
6. 交由评审门禁或返回用户确认

输出格式（示意）：

```yaml
plan:
  steps:
    - id: S<N>
      action: "..."
      inputs: [...]
      outputs: [...]
      depends_on: [S<M>]
      rollback: "..."
      # 数据订正步骤专用字段：
      prerequisite: storage_backend_confirmed
      script_language: "mongosh|sql|python|..."
      # 跨仓库步骤专用字段：
      repo: "ops-pilot-web"
      execution_strategy: "subagent|separate_session|manual_handoff"
  dependencies: [...]
  evidence: [...]
  verification_strategy:
    - { step: S<N>, method: "...", criteria: "..." }
  status: frozen
```

## 输出契约
- `snapshot.plan`（`status: frozen`）与 `plan_summary.md`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 快照缺失 → 降级为独立模式，自行初始化最小快照
- 门禁不通过 → 拒绝冻结，返回上游阶段
- 计划无法收敛 → 升级 `pax-council`

## 何时升级
- 门禁不通过 → 返回上游阶段
- 计划无法收敛或高风险 → `pax-council`
- 需要独立评审 → `pax-review`
- 需要环境事实或独立运行 → `pax-worker-*`
