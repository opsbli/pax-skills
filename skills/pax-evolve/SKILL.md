---
name: pax-evolve
description: >
    Use when: OODA 闭环 + 经验条目库 + A/B 验证门 + 回滚。汇总过往执行留痕（执行反馈、失败案例、
    A/B 对比），沉淀经验条目并提出 Skill 文档 / 契约的改进建议，经 A/B 验证门与回滚机制闭环。
    由 pax-orchestrate 在评审/学习阶段按需委托调用（周期性自审与经验升级链），也可由任意 L0/L1/L2
    阶段在积累足够留痕后登记触发。
version: 1.0.0
family: pax
layer: L4
optional: true
requires_snapshot: true
status: active
---

# pax-evolve

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

## Execution Contract

- 前置门禁：可被任意 L0/L1/L2 调用；反馈或失败案例可读取
- 未通过门禁：返回 `blocked`
- 版本检查：`pax-ops/versions.json`
- 变更必须经过 A/B 验证门
- 支持回滚
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界

- 做什么：OODA 闭环（观察/定向/决策/行动） + 经验条目库 + A/B 验证门 + 回滚
- 不做什么：不认领路由落点、不改变主流程、不直接改代码

## 输入

- 必需：执行反馈或失败案例
- 可选：历史经验条目、A/B 对比基准

## 工作流

### E1 观察（Observe）

收集执行反馈与失败案例：

```yaml
observe:
  sources:
    - type: execution_feedback
      source: snapshot.execution
      timestamp: "<ISO8601>"
    - type: failure_case
      source: snapshot.review
      timestamp: "<ISO8601>"
    - type: trial_feedback
      source: user_feedback
      timestamp: "<ISO8601>"

  signals:
    - type: failure
      description: "存储后端未确认就写 MySQL 脚本"
      severity: high
      frequency: 1
    - type: deviation
      description: "执行偏离契约，修改了未授权文件"
      severity: medium
      frequency: 2
    - type: inefficiency
      description: "验证循环超过 3 次"
      severity: low
      frequency: 3
```

### E2 定向（Orient）

归纳问题类型、根因、影响面：

```yaml
orient:
  problem_type: process_gap | tool_gap | knowledge_gap | coordination_gap
  root_cause: "<问题根因>"
  impact_scope: local | module | system | cross_team
  impact_severity: low | medium | high
  patterns:
    - pattern: "数据订正前未确认存储后端"
      frequency: 1
      recurrence: likely
    - pattern: "跨仓库步骤未标注执行策略"
      frequency: 2
      recurrence: likely
  root_causes:
    - cause: "D2 阶段缺少存储后端确认检查"
      evidence: [E1, E2]
    - cause: "plan 阶段缺少跨仓库标注规则"
      evidence: [E3]
```

### E3 决策（Decide）

提出改进条目（写入经验库草稿）：

```yaml
decide:
  entries:
    - id: E001
      type: experience | improvement | rule
      statement: "数据订正前必须确认存储后端、ORM、迁移工具"
      rationale: "避免写错存储引擎的脚本"
      source: trial_feedback
      applies_to:
        - "所有涉及数据订正的 Skill (L1/L2)"
      status: draft
      confidence: high
      created_at: "<ISO8601>"

    - id: E002
      type: rule
      statement: "跨仓库步骤必须标注 repo 和 execution_strategy"
      rationale: "确保跨仓库操作有明确的执行策略"
      source: trial_feedback
      applies_to:
        - "所有涉及跨仓库操作的 Skill (L1/L2)"
      status: draft
      confidence: high
      created_at: "<ISO8601>"
```

**经验条目结构**：
```yaml
experience_entry:
  id: "E001"
  type: experience | improvement | rule | pattern
  statement: "<经验陈述>"
  rationale: "<为何有这个经验>"
  source: "<来源>"
  applies_to: ["所有相关 Skill (L1/L2)"]
  status: draft | review | active | deprecated
  confidence: high | medium | low
  created_at: "<ISO8601>"
  updated_at: "<ISO8601>"
  deprecated_by: null | "E002"
```

### E4 A/B 验证门（A/B Validation Gate）

**验证门规则**：
1. 至少保留一个基线版本
2. 对比指标明确（成功标准、偏差容忍度）
3. 失败或指标不达阈值 → 触发回滚

```yaml
ab_validation:
  baseline:
    version: "v1.0"
    metrics:
      - name: "数据订正成功率"
        value: 95
        threshold: 90
      - name: "脚本执行时间"
        value: 120
        threshold: 300
      - name: "偏差数量"
        value: 2
        threshold: 5

  candidate:
    version: "v1.1"
    changes:
      - "D2 阶段增加存储后端确认"
      - "plan 阶段增加跨仓库标注规则"
    metrics:
      - name: "数据订正成功率"
        value: 98
        threshold: 90
      - name: "脚本执行时间"
        value: 95
        threshold: 300
      - name: "偏差数量"
        value: 0
        threshold: 5

  comparison:
    pass: true
    delta:
      - metric: "数据订正成功率"
        delta: +3
        direction: improve
      - metric: "脚本执行时间"
        delta: -25
        direction: improve
      - metric: "偏差数量"
        delta: -2
        direction: improve

  decision: promote | rollback | continue_testing
  decided_at: "<ISO8601>"
```

### E5 行动（Act）

经 A/B 验证门通过后发布；失败则回滚：

```python
def act(ab_result):
    """执行行动"""

    if ab_result.decision == "promote":
        # 发布新版本
        return promote_version(ab_result.candidate)

    elif ab_result.decision == "rollback":
        # 回滚
        return rollback_version(ab_result.baseline)

    elif ab_result.decision == "continue_testing":
        # 继续测试
        return continue_testing(ab_result.candidate)

    else:
        return "blocked", "未知决策"
```

### E6 回滚机制（Rollback Mechanism）

**回滚触发条件**：
- A/B 验证失败
- 指标低于阈值
- 用户反馈负面
- 安全问题

**回滚流程**：
```python
def rollback(candidate):
    """回滚"""

    # 条件 1: 保留变更日志
    log_change(candidate)

    # 条件 2: 恢复基线
    restore_baseline()

    # 条件 3: 记录决策
    decision = {
        "action": "rollback",
        "from": candidate.version,
        "to": baseline.version,
        "reason": candidate.rollback_reason,
        "timestamp": "<ISO8601>"
    }

    return decision
```

**回滚记录**：
```yaml
rollback_record:
  id: "R001"
  from_version: "v1.1"
  to_version: "v1.0"
  reason: "A/B 验证失败：偏差数量超过阈值"
  metrics:
    - name: "偏差数量"
      baseline: 2
      candidate: 8
      threshold: 5
  decided_at: "<ISO8601>"
  decided_by: "pax-evolve"
  approved_by: "manual_approval"
```

### E7 经验库管理（Experience Library Management）

**经验库结构**：
```yaml
experience_library:
  version: "1.0"
  entries:
    - id: "E101"
      type: rule
      statement: >
        plan.plan.steps[] 必须在冻结前由 plan 文档 1:1 镜像生成；
        每个 step 必须含 id、action、verification_min_depth、touches 四字段。
      rationale: >
        若 snapshot.plan.steps 为空或与文档不匹配，pax-execute E4 无锚点可追踪，
        E8 evidence binding 也无法建立引用关系——这是 pax-md M1 会话（dc235ed1）
        bug 的根因：plan.steps 为空导致 execute 自行合并步骤、完成声明失约。
      source: "trial_feedback: pax-md M1 session (dc235ed1)"
      applies_to:
        - "pax-plan P2 / P7"
        - "pax-execute E3 / E4 / E8"
      status: review
      confidence: high
      created_at: "2026-10-15"
      updated_at: "2026-10-15"
      deprecated_by: null
      ab_baseline_session: "dc235ed1-7b7a-4901-b6ab-0df8be846670"
      ab_baselines: ["dc235ed1-7b7a-4901-b6ab-0df8be846670", "0b129f94-2fcb-47fd-b8a3-c5b092e27b19"]
      ab_baseline_count: 2
      ab_candidate_count: 0
      ab_status: "two_baselines_confirmed_no_candidate"
      ab_notes: >
        M1（dc235ed1）与 M2（0b129f94）均为未应用 E101 的基线，两份样本的
        plan.steps 均完全为空、无任何 verification_seals、未挂 pax-verify、断言深度均止于 D1——
        四个结构指标完全一致。M2 表面无用户手测暴露的 bug，实为 5/8 subtasks
        manual 状态为 pending 未验证。
        ⚠️ 用户后续手测后发现 M2 存在 6+ 个快捷键失效（含 M1 已修复的 Ctrl+N
        回归），根因为 src/lib/useShortcuts.ts:28 的 `!def.enabled` 把 undefined
        当 falsy——一个 JavaScript 可选字段 trap，导致所有未显式设 enabled:true 的
        快捷键被静默跳过。160/160 测试全绿，但测试未覆盖 dispatcher 层。
        候选任务尚存，不能 promote 到 active，但证据已足够强。
      promote_recommendation: >
        证据已支持从 review → active：
        - 2 基线完全一致（M1、M2）；
        - M2 6+ 个系统性 bug 均能由 E101 的 plan.steps 镜像门捕获；
        - E101 refinement 已完成（允许组合 step + parallel_parts）。
        剩余风险仅在于候选任务尚存，但风险-收益比已足够高。
        建议：下一个 feature_dev 任务启动时直接将 E101 升为 active，
        任务完成后回头确认 5 项指标是否全部改善。
    - id: "E102"
      type: rule
      status: review
      statement: "编译和单测最多是 D1；交互步骤没有实际观察结果不得完成。"
      applies_to: ["pax-execute E4/E8"]
    - id: "E103"
      type: rule
      status: review
      statement: "命中快捷键、点击、弹窗等交互信号时，路由必须追加 pax-verify。"
      applies_to: ["pax-orchestrate W4"]
    - id: "E104"
      type: rule
      status: review
      statement: "pending、非标准 execution_status 或无证据引用时，评审必须拒绝。"
      applies_to: ["pax-review R1"]
    - id: "E001"
      type: rule
      statement: "数据订正前必须确认存储后端"
      status: active
      confidence: high
      created_at: "2026-09-29"
      applied_count: 5
      success_rate: 100
    - id: "E002"
      type: pattern
      statement: "跨仓库步骤需要明确执行策略"
      status: active
      confidence: high
      created_at: "2026-09-29"
      applied_count: 3
      success_rate: 100
    - id: "E003"
      type: improvement
      statement: "验证循环超过 3 次时自动降级"
      status: deprecated
      deprecated_by: "E004"
      deprecated_at: "2026-10-01"
      reason: "被更优方案替代"
  stats:
    total: 3
    active: 2
    deprecated: 1
    avg_success_rate: 100
```

## 输出契约

- 经验条目（写入经验库草稿）
- A/B 验证结果
- 回滚决策记录，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式

- 反馈不足 → 返回 `blocked`，列出缺失
- A/B 未通过 → 自动回滚并记录决策
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 高风险改进或跨模块影响 → 请求人工审批
- 需要独立验证或文档沉淀 → 由主流程协调相应横切能力
