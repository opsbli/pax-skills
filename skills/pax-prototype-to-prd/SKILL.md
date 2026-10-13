---
name: pax-prototype-to-prd
description: >
  Use when: 需求工程上游——从原型（HTML/截图/Figma/Axure 等导出）生成结构化 PRD，
  并内建质量门禁与变更管理。当用户提供原型目录/截图/设计稿并要求"生成 PRD / 原型转 PRD /
  解析原型 / 校验 PRD"时使用。四阶段：原型解析 → PRD 生成（含 EARS 验收标准）→ 质量门禁
  （fail-closed）→ 变更管理。此 skill 由编排层按 prototype_to_prd 标注调用，不要直接选择。
version: 1.0.0
family: pax
layer: L1
optional: true
requires_snapshot: true
status: active
---

# pax-prototype-to-prd

## Overview

需求工程上游的执行落点。把原型（HTML 目录、截图、Figma/Axure 等导出）解析为**结构化 PRD**，
由一门 skill 串起四阶段：原型解析 → PRD 生成（每条功能配 EARS 验收标准）→ 质量门禁（缺章节/非
EARS 即阻断，fail-closed）→ 变更管理（PRD 更新后影响分析→提案→用户批准→传播下游）。产出写入
`snapshot.prd`，作为需求契约锚点，供下游设计/规划阶段消费。

## When to Use

编排层已标注 `prototype_to_prd`，或用户提供原型并明确要求产出 PRD。典型形态：

- 「把这个原型 HTML 目录转成 PRD」
- 「生成 PRD，带验收标准」
- 「帮我解析这份 Figma 导出，整理成功能清单和验收标准」
- 「PRD 我改了，帮我分析影响并传播」

涉及竞品背景/需求背景调研的，可复用研究阶段产出（数据流，不跨阶段调用）。

## Common Pitfalls

- 把 EARS 外自由文本当成可验证验收标准——非 EARS 必须降级为提示，不能算通过。
- 质量门禁缺失必备章节仍放行（违反 fail-closed）——必须阻断进入下游。
- 原型解析只提取文字而漏掉页面流转、控件交互、数据字典。
- 变更在用户批准前就传播到下游。
- 越界做设计/开发/测试——本 skill 止步于 PRD 契约。

## Verification Checklist

- [ ] 原型已解析（页面/控件/交互/数据字段）
- [ ] 每条功能需求有 EARS 验收标准，且可测试
- [ ] 质量门禁已跑：缺章节/非 EARS 均有明确阻断判定
- [ ] 变更管理：未获批准不传播
- [ ] 写入 `snapshot.prd`，可被下游消费

## Execution Contract

- 前置门禁：`snapshot.orchestration.annotations.prototype_to_prd == true`，或用户显式提供原型并要求产 PRD 且快照已初始化
- 未通过门禁：拒绝启动，返回 `blocked` 并列出缺失（无原型输入请先补原型或回澄清阶段）
- 版本检查：读取 `pax-ops/versions.json` 校验家族版本
- 门禁 fail-closed：PRD 缺必备章节 / 验收标准非 EARS 格式 → `verification.verdict = FAIL` 并阻断进入下游，不允许降级继续
- 变更需用户批准：`change.status = pending_approval` 时不得传播任何下游
- 跳过留痕：任何跳过记录 `skip_reason`（无原型输入的咨询类任务应跳过此 skill）

## 职责边界

- **做什么**：原型解析、PRD 组装（含 EARS）、质量校验、变更影响分析与传播
- **不做什么**：不做设计（ADR/接口/数据模型）、不开发、不测试、不部署、不做需求调研本身的裁决、
  不认领 clarify/design/plan/execute/review 落点

## 输入

- 必需：原型输入（HTML 目录/单文件、截图、Figma/Axure 导出路径或描述）、`snapshot.goal.statement`
- 可选：`snapshot.orchestration`、`snapshot.consensus`（澄清结果）、研究阶段候选（数据流）、既有 `snapshot.prd`（变更场景）

## 工作流

### P1 原型解析（Prototype Parsing）

- 识别原型来源类型：HTML 目录 / 截图 / Figma / Axure / 墨刀 / MasterGo 等。
- 提取页面树：`pages`（route / layout / 元素）。
- 提取控件与交互：按钮、表单、跳转、弹窗等。
- 提取数据字段：表单与表格中的 `data_dictionary`（field / type / required）。
- 识别页面流转：`page_flow`（from / to / trigger）。

### P2 PRD 生成（PRD Generation，含 EARS）

- 按页面/模块提炼功能需求，每条：`id`（REQ-<AREA>-NNN）+ 一种 **EARS 句式** +
  可派生的 Given/When/Then 验收标准 + MoSCoW 优先级。
  EARS 五种句式：WHEN（事件）/ WHILE（状态）/ WHERE（可选功能）/ IF-THEN（非期望）/
  THE SYSTEM SHALL（不变式）。
- 组 `functional_requirements`、`acceptance_criteria`、`non_functional`（可衡量目标）、
  `scope`（in / out）、`open_questions`、`data_dictionary`。
- 可选：若已获研究阶段候选，将其竞品/背景部分并入（数据流，不重新裁决）。

### P3 质量门禁（Quality Gate，fail-closed）

按清单校验 PRD，产出 `verification`：

| 校验维度 | 要求 |
|---|---|
| 必备章节 | Executive Summary / Problem / Goals / 功能需求 / 验收标准 / 验证计划 |
| 验收标准格式 | 必须 EARS；非 EARS 视为自由文本，不算可验证标准 |
| 非功能需求 | 必须有可衡量目标值 |
| 范围边界 | In / Out 明确 |
| 验收判定 | `verdict`: PASS / NEEDS_WORK / FAIL |

- 缺必备章节或验收标准非 EARS → `FAIL`，**阻断进入设计/规划阶段**（fail-closed）。
  验收标准中存在任何自由文本（非 EARS）都会导致 FAIL，不得 PASS；「用户应该能用」这类无法验证的
  陈述一律视为不可验证标准。
- `NEEDS_WORK`：有提示项但可放行（附建议）。
- 不在任何 `FAIL`/`NEEDS_WORK` 情形下降级继续（对齐家族门禁哲学）。

### P4 变更管理（Change Management）

当输入为既有 PRD 的更新（`snapshot.prd` 已存在）：

1. **变更识别**：diff 新旧 PRD，识别变更内容与原因。
2. **影响分析**：评估对 PRD 章节 / 设计 / 任务 / 测试的影响。
3. **变更分类**：新建 / 更新现有 / 无需操作。
4. **变更提案**：产出 `change`（change_id / impact_analysis / status = pending_approval）。
5. **用户批准**：`pending_approval` 时等待用户确认，未批准不传播。
6. **传播**：`approved` 后更新受影响章节并通知下游（数据流，交设计/规划/测试阶段）。

**传播是硬门禁（fail-closed）**：`change.status` 非 `approved` 时，即使被用户要求「先直接传播 /
先让下游动起来」也必须停下等待明确批准；任何在未批准前的传播都是契约破坏，不得因催促或指令而放行。

## 输出契约

写入 `snapshot.prd`（格式由 `schemas/snapshot.schema.json` 约束）并追加 `meta.skill_lineage`：

```yaml
prd:
  source: {type: html|image|figma|axure, path: "<输入>"}
  pages: [{name, route, elements}]
  features:
    - {id: REQ-<AREA>-NNN, module: "<模块>", priority: must|should|could}
  functional_requirements:
    - {id, area, ears: "<EARS 句式>", acceptance: {given, when, then}, priority}
  acceptance_criteria:
    - {id, ears, testable: true}
  data_dictionary:
    - {field, type, required, description}
  scope: {in: [...], out: [...]}
  verification:
    verdict: PASS | NEEDS_WORK | FAIL
    findings: [{section, issue, severity, suggestion}]
  change:
    change_id: "<id>"          # 变更场景
    change_type: create | update | no_action
    impact_analysis: [{artifact, change, rationale}]
    status: pending_approval | approved | applied
```

不改动 `snapshot.diagnosis` / `plan` / `execution` / `review`。

## 失败模式

- 无原型 / 原型不可解析 → 返回 `blocked`，请求补充原型或明确输入
- 质量门禁 FAIL 不阻断 → 视为契约破坏，必须 fail-closed
- 变更未获批准传播 → 视为契约破坏，必须停在 pending_approval
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- PRD 已冻结、待方案 → 交设计阶段产出 ADR/接口/数据模型（数据流）
- PRD 已冻结、待排期 → 交规划阶段产出任务计划（数据流）
- 依赖需求背景调研但无研究候选 → 由编排按需补充研究阶段（不在此承接）
