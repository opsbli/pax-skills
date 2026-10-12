---
name: pax-research
description: >
  Use when: 开发前研究/发现阶段。当需求模糊、需调研需求背景、比对竞品、做技术选型、
  判断"值不值得做"时，把模糊问题拆成可检索子问题，调度有界检索收集外部事实，产出
  可交接的候选集（research 候选段）。此为 L1 只读采集阶段，**只出候选、不做裁决**；
  评估/裁决移交 pax-advisor / pax-council，方案定稿移交设计阶段。低风险/目标明确任务不需要。
  此 skill 由编排层按 research_required 标注挂载调用，不要直接选择。
version: 1.0.0
family: pax
layer: L1
optional: true
requires_snapshot: true
status: active
---

# pax-research

## Overview

开发前发现阶段（pre-development discovery）的只读采集落点。针对「需求调研、竞品比对、
技术选型、方案可行性」类任务，把模糊目标拆成可证伪子问题，调度有界检索收集外部事实
（来源可信度分级），沿子问题收敛出**候选集**写入 `snapshot.research`。它解决的是
「信息采集从哪里来」，不解决「选哪个」——所有产出按家族「AI 产出为候选」原则标记，
未经评估/用户确认不得写成结论。

## When to Use

编排层已标注 `research_required`（典型：`feature_dev` / `tool_build` 且不确定性 ≥ 2），
或用户表达「调研 / 看竞品 / 选哪个技术 / 值不值得做 / 市场背景」等意图。典型形态：

- 「我想做一个消防教培平台，先看看市场和技术选型」
- 「消息队列选哪个？帮我对比 Kafka / RabbitMQ / Pulsar」
- 「这个需求值不值得做，竞品怎么实现的」
- 「选技术栈，给几套方案比一下」

研究完成后，评估与裁决不在此承接：选型权衡交 `pax-advisor` 证据加权评估，高风险选型交
`pax-council` 盲审，方案定稿交设计/规划阶段（数据流，不跨阶段调用）。

## Common Pitfalls

- 越界做成裁决/冻结——本 skill 只出候选，选型结论、技术决策一律不得写成 `confirmed`。
- 结论无来源或来源未分级，无法回溯。
- 子问题发散不收束，调研无终点。
- 用单点检索代替综合对比，或把「搜索到了」当「该选了」。
- 把候选误当事实传入下游（违反「AI 产出为候选」契约）。

## Verification Checklist

- [ ] 采集范围只读，未修改任何业务状态
- [ ] 每条事实/候选标注来源（source / method / credibility / confidence）
- [ ] 产出收敛为候选集，`recommendation_candidate` 非最终结论
- [ ] 写入 `snapshot.research`，必要时交评估/裁决阶段

## Execution Contract

- 前置门禁：`snapshot.orchestration.annotations.research_required == true`，或用户显式表达研究意图且快照已初始化
- 未通过门禁：拒绝启动，返回 `blocked` 并列出缺失（目标模糊先回澄清阶段收敛）
- 版本检查：读取 `pax-ops/versions.json` 校验家族版本
- 只读：不修改 `snapshot.diagnosis` / `plan` / `execution` / `review` 等下游段
- 沙箱：仅做只读检索/采集，不执行写操作与破坏性命令
- 候选性：一切产出以候选形式写入 `*_candidates` 或标 `confidence`，不得写 `confirmed`/`settled`/`locked`
- 跳过留痕：任何跳过记录 `skip_reason`（不满足 research_required 的编排任务应跳过研究）

## 职责边界

- **做什么**：拆研究子问题、多源采集、来源可信度分级、组织候选集、交接评估/裁决
- **不做什么**：不做技术选型裁决、不产出可冻结契约（ADR/接口/数据模型）、不写业务文件、
  不认领 clarify/design/plan/execute/review 落点、不把候选写成分结论

## 输入

- 必需：`snapshot.goal.statement`、`snapshot.orchestration`（含 intent / route / annotations，确认 `research_required`）
- 可选：`snapshot.consensus`（澄清结果）、已有 `snapshot.analysis` / `snapshot.design.candidates`、目标领域/竞品清单

## 工作流

### R1 研究边界与只读确认（Research Scope）

```yaml
research_scope:
  read_only: true
  targets:
    - type: web | docs | code | market | competitor | api
      value: "<研究对象>"
  allowed_reads: ["公开资料", "文档", "仓库只读", "市场信息"]
  forbidden: ["写文件", "数据订正", "部署", "任何破坏性命令"]
```

- 确认目标与来源，明确「研究什么、不碰什么」。
- 若用户隐含裁决/落地诉求，返回编排在澄清约束下继续，不在此越界。

### R2 研究问题拆解（Sub-Question Decomposition）

把 `goal.statement` 拆成可证伪、可检索的 RQ1..RQn：

| 子问题 | 待验证点 | 证据类型 | 来源 |
|---|---|---|---|
| RQ1 | 需求背后的真实问题/动机 | market_demand | 行业/社区 |
| RQ2 | 竞品如何解决 | competitive | 竞品文档/站点 |
| RQ3 | 可选技术方案与成熟度 | tech_landscape | 官方文档/对比 |
| RQ4 | 大致成本与风险 | feasibility | 定价/约束 |

原则：每个子问题收敛一组可判定事实；无法判定的标记 `open_question`。

### R3 多源采集与可信度分级（Multi-source Collection）

调度有界检索收集事实（pax-research 为 L1，可调用 L3 `pax-worker-research` 合法）：

```
for each sub-question RQ:
    - 确定来源类型与可信度（官方文档 > 社区/竞品 > 泛搜索/推断）
    - 收集支持证据与反证
    - 每条证据标注 source / type / credibility / confidence
    - 区分「事实」与「推断」，推断必须降级可信度
```

worker 支持的类型：`web` / `documentation` / `competitive` / `code` / `market` / `api`。

### R4 候选组织（Candidate Synthesis，不裁决）

- 沿子问题逐项收拢：支持 + 反证并陈，标可信度。
- 组织候选集：`competitors`、`alternatives`（可选方案含 pros/cons 与证据）、`recommendation_candidate`。
- **所有项都是候选**，`recommendation_candidate` 仅表示「当前证据下的偏好方」，不是结论。
- 证据矛盾 → 降可信度并显式列 `open_questions`，不强行闭环。

### R5 交接（Handoff，数据流）

- 把候选集写入 `snapshot.research`，并追加 `meta.skill_lineage`。
- 选型权衡进一步评估 → 委托 `pax-advisor`（A2 候选生成 + A3 证据加权，只读）。
- 高风险选型 → 委托 `pax-council` 盲审。
- 方案定稿 → 交设计阶段/规划阶段消费候选（按阶段名表达数据流，不跨阶段调用）。
- 需求仍模糊 → 回澄清阶段收敛。

## 输出契约

写入 `snapshot.research`（格式由 `schemas/snapshot.schema.json` 约束）并追加 `meta.skill_lineage`：

```yaml
research:
  question: "<研究问题>"
  scope: "<范围>"
  sources:
    - url: "<来源>"
      type: documentation | competitive | market | ...
      credibility: high | medium | low
  findings:
    - id: F1
      sub_question: "RQ1"
      claim: "<候选事实>"
      evidence: "<来源引用>"
      confidence: high | medium | low
      is_inference: true | false
  competitors:
    - name: "<竞品>"
      features: ["..."]
      positioning: "<定位>"
  alternatives:
    - option: "<方案>"
      pros: ["..."]
      cons: ["..."]
      evidence: ["..."]
  recommendation_candidate: "<当前证据下的偏好方（候选，非结论）>"
  confidence: high | medium | low
  open_questions: ["<未收敛项>"]
  read_only: true
```

不改动 `snapshot.diagnosis` / `plan` / `execution` / `review`。

## 失败模式

- 目标模糊 / 范围缺失 → 返回 `blocked` 并列出缺失，请求先澄清
- 证据不足 / 无法分级 → 降可信度，列 `open_questions`，不强行下结论
- 检索不足综合 → 标记 `partial`，附检索范围与建议
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 研究后进入评估/裁决：选型权衡 → 委托 `pax-advisor`；高风险 → 委托 `pax-council`
- 任务实际需要落地（写代码/写文件/改数据）→ 返回编排走完整路由
- 需求背景不可能从外部获得、需用户拍板 → 回澄清阶段收敛
