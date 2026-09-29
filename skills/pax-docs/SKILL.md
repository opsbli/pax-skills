---
name: pax-docs
description: >
  把已确认硬决策沉淀为 CONTEXT.md 与 ADR。当评审门禁通过后，需要将硬决策、经验条目或故障档案落地为文档时使用。
version: 0.1.0
family: pax
layer: L4
optional: true
requires_snapshot: true
---

# pax-docs

## Execution Contract
- 前置门禁：可被任意 L0/L1/L2 调用；输入为已确认的硬决策或已产出的经验条目
- 未通过门禁：返回 `blocked`
- 版本检查：`pax-ops/versions.json`
- 增量写入，不污染正式文档
- 草稿区与正式区分离
- 最后统一审核后合并
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：把已确认硬决策沉淀为 `CONTEXT.md` 与 ADR
- 不做什么：不认领路由落点、不改变主流程、不覆盖既有正式文档

## 输入
- 必需：快照中已确认的硬决策或经验条目
- 可选：目标文档路径、ADR 编号、作者信息

## 工作流
1. 从快照抽取已确认硬决策与经验条目
2. 起草 `CONTEXT.md` 追加块与 ADR 草稿
3. 写入草稿区（草稿文件 + 变更清单）
4. 统一审核后合并到正式区

ADR 结构（示意）：
- 背景（Context）
- 决策（Decision）
- 理由（Rationale）
- 影响（Impact）
- 关联（References）

## 输出契约
- `CONTEXT.md` 增量块
- `ADR-<N>.md` 草稿或正式版
- 变更清单，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 硬决策缺失 → 返回 `blocked`
- 与既有正式文档冲突 → 保留草稿，请求人工裁决
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 高风险或涉及架构级文档冲突 → 请求人工审批
