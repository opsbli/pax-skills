---
name: pax-advisor
description: >
    Use when: 只读顾问，针对特定假设、权衡、架构问题提供咨询。当前未接线：家族内无任何 skill 调用本 skill；如需启用，先在调用方（如 pax-review 或 L1 阶段）显式登记触发条件。
version: 1.0.0
family: pax
layer: L2
optional: true
requires_snapshot: true
status: skeleton
---

# pax-advisor

> **状态：骨架（未接线）**。本 skill 无生产路由，正文已移至 `references/full-body.md`。
> 如需启用，先在调用方显式登记触发条件，再将 `status` 改为 `active` 并恢复正文。

## Overview

单点咨询 Skill。针对一个具体问题给出建议，不改动任何状态。

## When to Use

用户或上层 Agent 想要一个专家观点，但不希望触发完整执行流程。

## Common Pitfalls

- 建议过宽泛，缺乏可执行性。
- 越界触发本应交给多专家盲审的决策。
- 未留下建议留痕。

## Verification Checklist

- [ ] 建议针对单一问题，边界清晰
- [ ] 建议附有依据与不确定性说明
- [ ] 建议留痕写入快照，可以追溯

## 职责边界

- **做什么**：针对特定假设、权衡、架构问题提供咨询意见
- **不做什么**：不修改快照、不改变主流程、不认领路由落点、不产出可冻结契约

## 输入

- 必需：完整快照或明确的咨询问题
- 可选：上下文材料、历史决策、候选方案清单

## 输出

- 咨询意见文本（不写入快照）
- 可选附带：候选方案表、证据权重、异议清单

## 失败模式

- 信息不足 → 声明 `blocked` 并列出缺失
- 只存在单一候选 → 声明 `partial`，附推荐与不确定性
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 高风险或跨系统决策 → 转多层盲审机制处理
- 需要独立验证 → `pax-verify`

## Execution Contract

- 前置门禁：**无**——本 skill 为 `status: skeleton`，未接线，不参与运行时路由，因此没有门禁。
- 未通过门禁：不适用。
- 启用前 MUST 先恢复正文（`references/full-body.md`）并把 frontmatter 的 `status` 改为 `active`。

## 工作流

骨架状态下不执行工作流。完整工作流（A1–A6）见 `references/full-body.md`。

## 输出契约

骨架状态下不产出任何产物。完整的输出契约见 `references/full-body.md`。