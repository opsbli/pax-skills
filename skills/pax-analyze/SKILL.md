---
name: pax-analyze
description: >
  Use when: doc_consult 路由中承担只读分析/调研。当需要读代码、追数据链路、
  溯源写入时机、解释行为、梳理事实并产出有证据链的结论，且不修改业务状态时使用。
  此 skill 由 pax-orchestrate 在 doc_consult 路由中编排调用，不要直接选择。
version: 1.0.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-analyze

## Overview

doc_consult 路由的只读分析执行落点。针对「代码结构梳理、数据写入链路溯源、
行为解释、事实调研」类任务，把模糊问题拆成可证伪子问题，调度有界检索收集证据，
沿子问题收敛出有证据链的结论，并在用户需要时沉淀为记录。**不修改业务状态、不修复、不产出可冻结契约。**

## When to Use

编排层已把任务分类为 `doc_consult` 且路由进入 `analyze` 阶段。典型形态：

- 「帮我分析这个接口的数据，是什么时候写入 ES 的」
- 「这条链路哪里断了 / 数据为什么为 0」
- 「解释这段代码 / 这个配置的作用」
- 「对比 A 与 B 两种实现的事实差异」

完整走查样例（含每个阶段产出与 `snapshot.analysis` 落点）见 `references/examples.md`，
覆盖「数据链路溯源」与「行为解释 + 方案对比」两类典型场景。

## Common Pitfalls

- 越界做修复或写操作——本 skill 只读，发现需修复应返回编排重分类。
- 结论无证据链或证据未标注来源/方法/置信度。
- 子问题发散不收束，调研无终点。
- 把单点检索代替综合结论。

## Verification Checklist

- [ ] 分析范围只读，未修改任何业务状态
- [ ] 每条结论附有证据链（source / method / confidence / timestamp）
- [ ] 收敛到明确结论 + 置信度 + 未解释残差
- [ ] 写入 `snapshot.analysis`，必要时沉淀为记录

## Execution Contract

- 前置门禁：`snapshot.orchestration.intent.primary == "doc_consult"` 且 `"analyze" in snapshot.orchestration.route`
- 未通过门禁：拒绝启动，返回 `blocked` 并列出缺失（非 doc_consult 请回编排重分类）
- 版本检查：读取 `pax-ops/versions.json` 校验家族版本
- 只读：不修改 `snapshot.diagnosis` / `plan` / `execution` / `review` 等下游段
- 沙箱：仅读取目标仓库/路径/数据源，不执行写操作与破坏性命令
- 跳过留痕：任何跳过记录 `skip_reason`

## 职责边界

- **做什么**：拆子问题、收集证据、合成结论、记录分析
- **不做什么**：不修复缺陷、不修改数据、不写业务文件、不产出可冻结契约、不认领 diagnose/plan/execute/review 落点

## 输入

- 必需：`snapshot.goal.statement`、`snapshot.orchestration`（含 intent / route / annotations）
- 可选：`snapshot.consensus`（doc_consult 澄清结果）、目标路径/文件/数据源、`references/domain-dependencies.md`

## 工作流

### A1 只读边界确认（Read-only Scope）

```yaml
analysis_scope:
  read_only: true
  targets:
    - type: repo_path | file_path | config | data_source | query
      value: "<目标>"
  allowed_reads: ["src/", "config/", "script/", "相关日志与存储查看"]
  forbidden: ["写文件", "数据订正", "部署", "任何破坏性命令"]
```

- 确认目标与读取来源，明确「允许读什么、绝不碰什么」。
- 若用户请求隐含修复/写操作，返回编排重分类，不在此承接。

### A2 子问题拆解（Sub-Question Decomposition）

把 `goal.statement` 拆成可证伪、可检索的子问题 Q1..Qn：

| 子问题 | 待验证点 | 证据类型 | 来源 |
|---|---|---|---|
| Q1 | 数据写入链路入口在哪 | code_search | grep / AST |
| Q2 | 数据是否/何时写入 ES | runtime_probe / configuration | 日志、存储查看 |
| Q3 | 返回 0 的原因分支 | code_search | 分支与条件阅读 |

原则：每个子问题收敛一个可判定事实；无法判定的标记为 `open_question`。

### A3 证据收集（Evidence Collection）

调度有界检索 worker 收集事实（pax-analyze 为 L1，可调用 L3 `pax-worker-research` 合法）：

```
for each sub-question Q:
    - 确定检索源（文件系统 / 配置 / 日志 / 只读查询）
    - 收集匹配与反证证据
    - 每条证据标注 source / method / confidence / timestamp
    - 缓存同会话已获取的环境事实，避免重复检索
```

worker 支持的类型：`code_search` / `documentation` / `dependency` / `configuration` / `runtime_probe`。

### A4 结论合成（Conclusion Synthesis）

- 沿子问题逐项收敛：支持证据 + 反证证据并陈，标注重信度。
- 汇总为一条主结论（`conclusion`），给出 `confidence`（high / medium / low）。
- 未解释的残差写入 `open_questions[]`，不强行闭环。
- 证据矛盾 → 降置信度并显式列残差。

### A5 可选沉淀与回报（Optional Persist）

- 用户需要留档 / 结论值得固化时，调用 L4 `pax-docs` 沉淀为分析记录（doc_consult 分支，轻量）。
- 否则仅把结论回写 `snapshot.analysis` 并向父会话汇报，不再强制产出 ADR。

## 输出契约

写入 `snapshot.analysis`（格式由 `schemas/snapshot.schema.json` 约束）并追加 `meta.skill_lineage`：

```yaml
analysis:
  findings:
    - id: F1
      sub_question: "Q1"
      statement: "<结论>"
      evidence:
        - source: "<文件/日志/来源>"
          method: code_search | runtime_probe | ...
          content: "<证据内容引用>"
          confidence: high | medium | low
      supports: true | false
  conclusion: "<主结论一句话>"
  confidence: high | medium | low
  open_questions:
    - "<未解释残差>"
  read_only: true
```

不改动 `snapshot.diagnosis` / `plan` / `execution` / `review`。

## 失败模式

- 信息不足 / 目标缺失 → 返回 `blocked` 并列出缺失项，请求补充上下文
- 证据矛盾 → 降置信度，列残差，不强行下结论
- 单一路径检索不足以综合 → 标记 `partial`，附检索范围与建议
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 任务实际需要修复 / 写数据 / 改行为 → 返回编排阶段重分类为 `diagnose_fix` / `data_ops` / `feature_dev` 走完整路由
- 分析中遇「权衡 / 架构决策型咨询」（超出只读事实分析范围）→ 委托 `pax-advisor` 提供候选方案与依据（只读，不改状态）
- 需要独立复核结论 → 交由 `pax-review` 轻量走一遍（仅当用户要求）
