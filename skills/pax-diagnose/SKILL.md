---
name: pax-diagnose
description: >
  对 bug、故障、性能退化、回归进行根因诊断。当用户报告异常、报错或性能下降，且编排判定需要根因分析时使用。
version: 0.1.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-diagnose

## Execution Contract
- 前置门禁：`snapshot.symptom` 已记录，且 `orchestration.diagnose_required == true`
- 未通过门禁：拒绝启动，返回用户补齐症状描述
- 版本检查：`pax-ops/versions.json`
- 跳过留痕：任何跳过必须记录 `skip_reason`（跳过留痕契约）
- 禁止在 D5 之前输出 `root_cause`
- 禁止在根因假设未验证前输出 `root_cause`
- `severity: P0` 时禁止进入规划阶段，必须升级 `pax-council`
- 所有 RC 未确认时 status 保持 `pending`，不进入下一阶段
- 禁止修改代码或执行修复

## 职责边界
- 做什么：对 bug、故障、性能退化、回归进行根因诊断，产出诊断报告与回归范围
- 不做什么：不修改代码、不执行修复、不做任务规划

## 输入
- 必需：`snapshot.symptom`
- 可选：日志、变更记录、指标、依赖版本

## 工作流
D1→D6 强制顺序，任何跳过必须记录 `skip_reason`。

1. **D1 复现（Reproduce）**
   - 输出：`reproduction.{status, method, observed, error_signature, environment}`
   - `status ∈ {reproduced, not_reproduced, partial}`
2. **D2 证据收集（Evidence Collection）**
   - 输出：`evidence[]`（`type ∈ {log, stack_trace, change, metric, config, dependency}`）
3. **D2.5 历史诊断检索**（自动执行）
   - 检索源：`pax-docs` 维护的故障档案、历史 snapshot、issue/PR
   - `similarity: high` 时，D3 假设生成必须优先验证历史根因
4. **D3 假设生成（Hypothesis Generation）**
   - 输出：`hypotheses[]`，每条含 `statement`、`supporting_evidence`、`contradicting_evidence`、`test_method`
5. **D4 假设验证（Hypothesis Validation）**
   - `status ∈ {confirmed, rejected, inconclusive}`，记录 `test_performed` 与 `result`
6. **D5 根因收敛（Root Cause Convergence）**
   - 输出：`root_cause.{statement, confidence, severity, severity_rationale, minimal_repro, regression_scope[]}`
7. **D6 报告产出（Report）**
   - 输出：`diagnosis_report.md` 与 `review_checklist`（RC1–RC7）

**信息不足声明机制**：任何一步证据不足时输出 `status: blocked`，附 `blocked_at` 与 `missing_information`；禁止用"可能""大概""疑似"填充证据缺口。

**RC 拒绝回退映射**：

| RC | 回退到 |
|---|---|
| RC1 | D1 |
| RC2 / RC6 | D3 / D4 |
| RC3 / RC4 / RC5 | D5 |
| RC7 | D2 |

**严重度量化**：

- **P0**：核心流程完全不可用 / 影响所有用户 / 无规避 / 安全相关 → 强制升级 `pax-council`
- **P1**：核心流程部分不可用 / 影响部分用户 / 有临时规避 → 走 `plan → execute → review`
- **P2**：非核心流程部分不可用 / 影响少量用户 / 有明显规避 → 可合并到常规迭代

## 输出契约
- `snapshot.diagnosis`（含 `reproduction` / `evidence` / `hypotheses` / `root_cause` / `review_checklist`）
- `diagnosis_report.md`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 证据不足 → `status: blocked`，附 `blocked_at` 与 `missing_information`
- `severity: P0` → 禁止进入规划阶段，升级 `pax-council`
- RC 检查失败 → 按上表回退到对应步骤
- 跳过任何 D 步骤 → 必须记录 `skip_reason`

## 何时升级
- `severity: P0` 或涉及架构级根因 → `pax-council`
- 需要历史档案检索 → `pax-docs`
- 需要独立复现 → `pax-worker-*`
- 需要独立评审 → `pax-review`
