---
name: pax-evolve
description: >
    Use when: OODA 闭环 + 经验条目库 + A/B 验证门 + 回滚。当前未接线：家族内无任何 skill 调用本 skill；如需启用，先在调用方显式登记触发条件。
version: 1.0.0
family: pax
layer: L4
optional: true
requires_snapshot: true
status: skeleton
---

# pax-evolve

> **状态：骨架（未接线）**。本 skill 无生产路由，正文已移至 `references/full-body.md`。
> 如需启用，先在调用方显式登记触发条件，再将 `status` 改为 `active` 并恢复正文。

## Overview

自进化 Skill。汇总过往执行留痕，提出 Skill 文档 / 契约的改进建议。

## When to Use

定期或积累足够执行留痕后，主动或按需运行。

## Common Pitfalls

- 建议过于主观，缺乏证据支撑。
- 建议破坏现有契约兼容性。
- 未走 PR / review 流程直接落盘。

## Verification Checklist

- [ ] 每条改进建议都有支撑证据
- [ ] 建议与兼容矩阵一致
- [ ] 改动以 PR / patch 形式提交，不直接改生产文件

## 职责边界

- **做什么**：OODA 闭环（观察/定向/决策/行动）+ 经验条目库 + A/B 验证门 + 回滚
- **不做什么**：不认领路由落点、不改变主流程、不直接改代码

## 输入

- 必需：执行反馈或失败案例
- 可选：历史经验条目、A/B 对比基准

## 输出

- 改进建议列表（以 PR / patch 形式提交）
- 经验条目更新
- A/B 验证结果

## 失败模式

- 信息不足 → 声明 `blocked`
- 建议破坏兼容性 → 拒绝提交
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 高风险变更 → 升级 `pax-council`
- 需要独立评审 → `pax-review`

## 正文

完整工作流（E1–E6）见 `references/full-body.md`。