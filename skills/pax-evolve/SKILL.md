---
name: pax-evolve
description: >
  OODA 闭环 + 经验条目库 + A/B 验证门 + 回滚。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 0.2.0
family: pax
layer: L4
optional: true
requires_snapshot: true
---

# pax-evolve

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
