---
name: pax-orchestrate
description: >
  路由、风险分级、生命周期管理、快照初始化。L0 层负责路由、风险分级与生命周期管理。
version: 0.1.0
family: pax
layer: L0
optional: false
requires_snapshot: true
---

# pax-orchestrate

## Execution Contract
- 前置门禁：能读取 `pax-family.schema.yaml` 与 `pax-ops/versions.json`
- 未通过门禁：拒绝启动，返回用户错误
- 版本检查：`pax-ops/versions.json`
- 记录义务：`diagnose_required` 决策必须附 `rationale`（若跳过诊断则附 `skip_reason`）
- 记录义务：风险评分必须写入四维原始分数与总分

## 职责边界
- 做什么：意图分类（MECE）、风险评分、`diagnose_required` 决策、路由构建、快照初始化
- 不做什么：不执行具体工作、不修改快照下游字段、不产出执行或评审结论

## 输入
- 必需：`user_goal`, `context`
- 可选：历史快照、领域依赖映射表

## 工作流
1. `intent = classify_intent(user_goal)`  # MECE 分类
2. `risk = assess_risk(user_goal, context)`  # 四维评分
3. `diagnose_required = is_diagnostic_intent(intent, context)`
4. `strategy = "batch" if risk <= 9 else "one-by-one"`
5. `route = build_route(intent, diagnose_required, risk)`
6. `return init_snapshot(intent, risk, diagnose_required, strategy, route)`

## 风险评分维度
- 不可逆性（1-3）
- 影响范围（1-3）
- 不确定性（1-3）
- 协调成本（1-3）

总分映射：4-6 低 / 7-9 中 / 10-12 高。

## 路由规则
- 诊断类意图（修复/报错/异常/回归/性能退化）
  → `[clarify, diagnose, plan, execute, review]`
- 普通任务 → `[clarify, plan, execute, review]`

跳过诊断必须显式记录 `skip_reason`，允许条件：
- 新建功能，无既有行为
- 根因已在 clarify 阶段完全确定且用户确认
- 纯文档、纯咨询、纯规划类任务
- 用户明确要求"先别查根因，直接改"

## 输出契约
- `snapshot.orchestration` 与快照初始状态，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 分类置信度低 → 降级为保守评分，并在路由中保留高风险标记
- 风险维度数据缺失 → 降级为保守评分（假设高不确定性）
- 用户目标过于模糊 → 进入澄清阶段后再路由

## 何时升级
- 高风险任务（总分 10-12） → 在路由中标记 `question_strategy: one-by-one` 并由下游阶段处理
- 高风险决策需盲审 → 在路由中标记升级建议，交由下游阶段协调
