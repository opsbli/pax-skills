---
name: pax-design
description: >
  Use when: 需求已澄清但方案未定时，产出可冻结的设计契约——架构决策记录、接口契约、数据模型、
  服务边界与可观测性设计，供 pax-plan 作为约束消费。触发场景包括：新系统或新模块的架构设计、
  接口契约定义、数据模型设计、技术选型定稿、高风险改动的方案评审。
  此 skill 由编排层在 clarify 与 plan 之间按需挂载，不要直接选择。
version: 1.0.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-design

## Overview

设计门禁 Skill。承接已澄清的需求，产出**可冻结的设计契约**（ADR / 接口契约 / 数据模型 /
服务边界 / 可观测性设计），使下游计划不必在「边写边猜架构」。本 skill 只做设计决策与契约
固化，**不写业务代码、不生成执行步骤、不改下游快照段**。

设计不是凭空创造，而是**收敛**：把上游分散的约束收敛成少数几条可追溯的决策，每条决策都带
权衡与后果，未收敛的部分显式留为开放问题而不是含糊通过。

## When to Use

编排层判定任务需要设计契约时挂载本 skill。典型形态：

- 「新系统/新模块怎么设计」「接口契约定一下」「数据模型设计」
- 技术选型需要定稿并留档（选型过程本身可委托只读顾问，本 skill 负责定稿与留痕）
- 高风险改动在计划前需要方案评审与盲审

**不适用**（不要挂载本 skill）：

- 纯 bug 修复、根因已确定、方案唯一 → 直接进计划阶段
- 纯文档/解释/事实调研 → 走只读分析路径
- 需求本身还没澄清 → 先澄清，设计无法在缺口未收敛时定稿

## Common Pitfalls

- **把设计当创作**：没有上游约束支撑就自造方案。应先确认约束来源，缺什么就列为开放问题。
- **无取舍的单方案**：高风险决策只给一个方案 = 没有决策。至少 2 个候选 + 明确取舍理由。
- **越界执行**：顺手把代码写了。设计 skill 写业务代码会让计划阶段失去约束意义。
- **契约不可执行**：接口契约只写「有哪些接口」，不写请求/响应/错误码，计划阶段无法消费。
- **可观测性事后补**：不做日志/指标/追踪设计，运维阶段无法落地。

## Verification Checklist

- [ ] `design_required` 判定有明确依据，跳过时写了 `skip_reason`
- [ ] 每个不可逆/高风险决策都有对应 ADR，且写了代价与后果
- [ ] 接口契约含请求/响应/错误码，可被下游直接消费
- [ ] 数据模型含实体关系与关键约束（唯一性/外键/索引意图）
- [ ] 服务边界写明职责与依赖方向，无循环依赖
- [ ] 可观测性含日志/指标/追踪/SLO 要点
- [ ] 未收敛项写入开放问题，未强行闭环
- [ ] 写入 `snapshot.design` 并追加 `meta.skill_lineage`

## Execution Contract

- 前置门禁：① 能读到 `snapshot.goal.statement` 与 `snapshot.consensus`；
  ② 上游澄清已收敛（`consensus.gaps_remaining` 中的阻塞级缺口已处置）；
  ③ 家族运行时 `pax-ops/versions.json` 可读
- 未通过门禁：**拒绝启动**，返回 `blocked` 并列出缺失项；不得以「先做一点设计」绕过
- 版本检查：`pax-ops/versions.json`（家族版本唯一来源，读家族运行时，非项目内副本）
- 只写 `snapshot.design` 与 `meta.skill_lineage`；不改 `plan` / `execution` / `review` /
  `consensus`（`consensus` 由澄清阶段独占，本 skill 只读）
- 冻结纪律：`design.status` 一旦为 `frozen`，修改需显式 `superseded_by` 指向新决策
- 独立：设计结论不引用执行结果作为依据（避免「因为已经这么写了所以设计如此」）
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）
- 沙箱：本 skill 不写业务代码、不执行部署、不触碰生产数据

## 职责边界

- **做什么**：收敛设计约束、产出 ADR、固化接口契约与数据模型、定义服务边界与可观测性设计、
  设计评审门禁、冻结设计契约
- **不做什么**：不写业务代码、不生成执行步骤与时间线、不做根因诊断、不评审已产出的代码、
  不做部署与监控配置、不认领计划/执行/评审的路由落点

## 输入

- 必需：`snapshot.goal.statement`、`snapshot.consensus`（澄清结果与设计树）、
  `snapshot.orchestration`（含 intent / risk / annotations）
- 可选：既有代码结构事实、上下游契约、历史决策记录、用户给定的约束清单

## 工作流

### D1 设计必要性判定（Design Required Decision）

先判「要不要设计」，再谈「设计什么」。

```python
def is_design_required(intent, risk, context):
    """判断是否需要进入设计阶段"""

    # 强制设计
    if intent.primary in ("feature_dev", "tool_build") and risk.level == "high":
        return True
    if "security" in intent.secondary:
        return True
    if "integration" in intent.secondary:
        return True

    # 强制跳过
    if intent.primary == "doc_consult":
        return False, "doc_consult_only"
    if intent.primary == "diagnose_fix" and risk.level == "low":
        return False, "root_cause_known_single_solution"

    # 条件判断
    if introduces_new_interface(context):
        return True
    if introduces_schema_change(context):
        return True
    if crosses_service_boundary(context):
        return True

    return False, "no_new_contract_no_boundary_change"
```

**跳过设计的允许条件**（必须写入 `skip_reason`）：

| 条件 | `skip_reason` 值 |
|---|---|
| 纯文档/咨询/调研 | `doc_consult_only` |
| 根因已确定且方案唯一、风险低 | `root_cause_known_single_solution` |
| 无新增接口/无 schema 变更/无跨边界改动 | `no_new_contract_no_boundary_change` |
| 用户明确要求「别设计了直接改」 | `user_explicit_skip` |

**不允许跳过设计的情况**：

- `risk.level == "high"` 且为 `feature_dev` / `tool_build`
- `intent.secondary` 含 `security` 或 `integration`
- 引入新接口、schema 变更或跨服务边界改动

### D2 设计深度判定（Design Depth）

| 深度 | 条件 | 必须产出 |
|---|---|---|
| `minimal` | 低风险、无新边界 | 一条决策记录 + 关键约束 |
| `standard` | 新增接口或 schema 变更 | ADR + 接口契约 + 数据模型 |
| `full` | 跨服务/高风险/技术选型定稿 | ADR（≥2 候选）+ 接口契约 + 数据模型 + 服务边界 + 可观测性设计 + 盲审 |

### D3 方案候选生成（Candidate Generation）

`full` 深度的高风险决策**必须给出 ≥2 个候选**，每个候选带证据与代价：

```yaml
candidates:
  - id: "C1"
    name: "<方案名>"
    approach: "<实现路径>"
    pros: ["<优点>"]
    cons: ["<缺点>"]
    evidence:
      - source: "<来源>"
        confidence: high | medium | low
    costs:
      - type: time | complexity | maintenance
        estimate: "<估计>"
  - id: "C2"
    ...
decision: "C1"
rationale: "<为何选它，代价是什么>"
```

**规则**：

- 单一方案 + 无候选对比 = 视同未决策，高风险下必须补候选或降级为 `minimal` 并说明理由。
- 证据不足的候选标 `confidence: low`，不得当作决策依据。
- 选型类决策的「不选什么」也要留痕（`rejected` + 理由），避免后续重复讨论。

### D4 架构决策记录（Architecture Decision Record）

每条 ADR 必须含**代价**——没有代价的决策说明还没想清楚：

```yaml
adrs:
  - id: "ADR-1"
    title: "<决策标题>"
    status: proposed | accepted | superseded
    context: "<约束与背景，来自上游澄清或环境事实>"
    decision: "<决定了什么>"
    alternatives: ["<被否方案 + 否决理由>"]
    consequences:
      positive: ["<收益>"]
      negative: ["<代价、风险、后续负担>"]
    supersedes: null
    decided_at: "<ISO8601>"
```

**规则**：

- 不可逆或跨边界决策必须有 ADR；可逆的实现细节不写 ADR（避免决策噪音）。
- ADR 不重复上游已有结论，只记录**新增的**设计决策及其依据。
- 状态为 `superseded` 时必须填 `supersedes` 指向被取代的 ADR id。

### D5 接口契约与数据模型（Contracts & Data Models）

**接口契约必须可被下游直接消费**——只列接口名不算契约：

```yaml
api_contracts:
  - name: "<接口名>"
    method: GET | POST | PUT | DELETE
    path: "<路径>"
    request: "<字段: 类型 | 必填 | 约束>"
    response: "<字段: 类型 | 语义>"
    error_codes:
      - code: "<错误码>"
        when: "<触发条件>"
    auth: "<认证要求>"
    version: "<版本策略>"
```

```yaml
data_models:
  - name: "<实体名>"
    fields:
      - name: "<字段>"
        type: "<类型>"
        constraints: "<唯一/非空/默认值/长度>"
    relationships:
      - "<实体> 1:N <实体>（外键字段）>"
    indexes: ["<查询意图 → 索引>"]
```

**规则**：

- 错误码与触发条件成对出现；无错误码的接口视为契约不完整。
- 数据模型必须写清查询意图与索引意图，否则迁移阶段无从验证。
- 涉及个人敏感字段时，`security_considerations` 必须写明脱敏与审计要求。

### D6 服务边界与可观测性设计（Boundaries & Observability）

```yaml
service_boundaries:
  - name: "<服务/模块名>"
    responsibility: "<单一职责一句话>"
    depends_on: ["<依赖的其它边界>"]
    exposes: ["<对外契约>"]
```

**规则**：`depends_on` 必须构成**有向无环图**；出现环必须合并边界或重切职责。

```yaml
observability_plan:
  logs: ["<日志规范：结构化字段、关键事件、敏感字段脱敏>"]
  metrics: ["<指标名: 语义 | 类型（counter/gauge/histogram）>"]
  traces: ["<跨服务调用链埋点位置>"]
  slo:
    - metric: "<指标>"
      target: "<目标值>"
      alert_threshold: "<告警阈值>"
```

**规则**：新增服务边界必须给 SLO 与告警阈值，否则运维阶段无判据。

### D7 设计评审门禁（Design Review Gate）

`full` 深度或 `risk.level == "high"` 时，把候选与 ADR 提交多专家盲审（`pax-council`，
只读评审，不改状态）。盲审结论写回 `snapshot.design.review`。

未获多数认可的 ADR 不得进入 `accepted`，也不得作为计划约束。

### D8 契约冻结（Design Freeze）

```python
def freeze_design(design):
    """冻结前自检：任一项缺失则拒绝冻结"""
    if design.depth in ("standard", "full") and not design.api_contracts:
        return "blocked", "缺少接口契约"
    if design.depth == "full":
        if not design.adrs:
            return "blocked", "缺少架构决策记录"
        if not design.observability_plan.slo:
            return "blocked", "缺少 SLO 与告警阈值"
    if has_cycle(design.service_boundaries):
        return "blocked", "服务边界存在循环依赖"
    return "frozen", None
```

自检通过才写 `status: frozen` 并记 `frozen_at`。**冻结失败返回 `blocked`，不得部分冻结。**

## 输出契约

写入 `snapshot.design`（格式由 `schemas/snapshot.schema.json` 约束）并追加
`meta.skill_lineage`：

```yaml
design:
  design_required: true | false
  skip_reason: "<跳过理由或 null>"
  depth: minimal | standard | full
  candidates: []
  adrs: []
  api_contracts: []
  data_models: []
  service_boundaries: []
  observability_plan: {}
  security_considerations: []
  review:
    required: true | false
    verdict: accepted | needs_revision | blocked | null
    round: 0
  open_questions: []
  status: draft | frozen | blocked
  frozen_at: "<ISO8601 或 null>"
```

不改 `consensus` / `plan` / `execution` / `review`。

## 失败模式

- 上游澄清未收敛 → 返回 `blocked`，列出阻塞缺口，回编排层重澄清（不在此硬设计）
- 候选方案无法收敛 → `status: draft`，写 `open_questions`，不冻结
- 盲审未通过 → `verdict: needs_revision`，按评审意见补候选，**不改**既有 ADR 措辞掩盖分歧
- 服务边界成环 → `blocked`，要求合并边界或重切职责
- 冻结自检失败 → `blocked` 并列出缺失项，**不得部分冻结**
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 需求本身不清晰、约束缺失 → 返回编排层重澄清（设计不能替代澄清）
- 选型需要独立方案评估（超出定稿范围）→ 委托只读顾问拿候选与依据
- 设计结论存在重大争议、盲审无法收敛 → 升级多专家盲审机制
- 需要独立复核设计可执行性 → 交由运行中验证（只读检查，不改设计）
- 需要把已冻结的设计沉淀为长期文档 → 走文档沉淀阶段（`consensus` 已定稿的设计不再重开）