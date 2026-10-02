---
name: pax-council
description: >
    Use when: 对重大系统开发计划做盲审、显式反驳、有界修订轮次、证据加权决策。
version: 0.2.0
family: pax
layer: L2
optional: true
requires_snapshot: true
---

# pax-council


## Overview

多专家盲审 Skill。并行召集多个专家 Agent 独立评审，再汇总分歧。

## When to Use

高风险、跨团队、或多视角必要；编排层判定为需要盲审的决策。

## Common Pitfalls

- 专家视角过窄，未覆盖风险、合规、性能等维度。
- 未隔离专家视角，导致回声室。
- 汇总时未处理分歧，直接采纳多数意见。

## Verification Checklist

- [ ] 已召集至少 3 个专家且视角互补
- [ ] 分歧已被显式记录并给出裁决理由
- [ ] 汇总结论有可执行结论与反对意见留痕
## Execution Contract
- 前置门禁：需要完整快照或明确的升级问题陈述
- 未通过门禁：拒绝启动
- 版本检查：`pax-ops/versions.json`
- 只读：不修改快照、不改变主流程、不认领路由落点
- 决策必须附证据与异议记录
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：对重大系统开发计划做盲审、显式反驳、有界修订轮次、证据加权决策
- 不做什么：不修改快照、不改变主流程、不认领路由落点

## 输入
- 必需：完整快照或明确的问题陈述
- 可选：历史决策、反对意见、备选方案

## 触发条件
- 高风险任务（`required_precision: high`）
- 诊断类任务 `severity: P0`
- 根因涉及架构级问题
- 疑似安全漏洞
- 评审阶段标记 `escalated`
- 澄清阶段无法收敛

## 工作流

### C1 问题收集（Problem Collection）

收集候选方案与证据：

```yaml
problem_statement:
  description: "<问题描述>"
  severity: P0 | P1
  scope: "<影响范围>"
  constraints:
    - "<约束条件>"
  stakeholders:
    - "<利益相关者>"

candidate_solutions:
  - id: "S1"
    author: "<提案者>"
    description: "<方案描述>"
    evidence:
      - id: "E1"
        source: "<证据来源>"
        weight: high | medium | low
        content: "<证据内容>"
    risks:
      - "<风险>"
    costs:
      - "<成本>"
  - id: "S2"
    ...
```

### C2 盲审（Blind Review）

隐藏提案者身份，独立评估每个方案：

```python
def blind_review(solutions):
    """盲审"""
    
    reviews = []
    
    for solution in solutions:
        # 隐藏提案者身份
        anonymized = {
            "id": solution.id,
            "description": solution.description,
            "evidence": solution.evidence,
            "risks": solution.risks,
            "costs": solution.costs
            # 不包含 author
        }
        
        review = {
            "solution_id": solution.id,
            "strengths": identify_strengths(anonymized),
            "weaknesses": identify_weaknesses(anonymized),
            "evidence_quality": assess_evidence_quality(anonymized.evidence),
            "risk_assessment": assess_risks(anonymized.risks),
            "recommendation": make_recommendation(anonymized)
        }
        reviews.append(review)
    
    return reviews
```

### C3 显式反驳（Explicit Rebuttal / Red-Team）

至少一轮 red-team 攻击：

```yaml
red_team_review:
  round: 1
  attacker_role: "red_team"
  attacks:
    - target: "S1"
      attack_type: "assumption_challenge"
      description: "方案 S1 假设所有用户都会升级，但实际可能有 20% 用户不会升级"
      severity: high
      evidence: "历史数据显示用户升级率约 80%"
    
    - target: "S1"
      attack_type: "edge_case"
      description: "方案 S1 没有处理并发场景，高并发下可能死锁"
      severity: medium
      evidence: "并发测试未在方案中提及"
    
    - target: "S2"
      attack_type: "cost_underestimation"
      description: "方案 S2 低估了迁移成本，实际需要 3 周而非 1 周"
      severity: medium
      evidence: "类似项目历史数据"
  
  responses:
    - attack_id: "A1"
      defense: "已添加用户升级引导机制"
      resolution: addressed
    - attack_id: "A2"
      defense: "已添加并发控制逻辑"
      resolution: addressed
    - attack_id: "A3"
      defense: "已重新评估时间，调整为 2 周"
      resolution: partially_addressed
```

### C4 有界修订轮次（Bounded Revision Rounds）

默认上限 2 轮，超过升级：

```python
def revision_rounds(solutions, max_rounds=2):
    """有界修订轮次"""
    
    current_solutions = solutions[:]
    rounds = []
    
    for round_num in range(max_rounds):
        # 收集反馈
        feedback = collect_feedback(current_solutions)
        
        # 修订方案
        revised = revise_solutions(current_solutions, feedback)
        
        # 记录轮次
        rounds.append({
            "round": round_num + 1,
            "changes": diff_solutions(current_solutions, revised),
            "remaining_issues": identify_remaining_issues(revised)
        })
        
        # 检查是否收敛
        if has_converged(revised):
            break
        
        current_solutions = revised
    
    if round_num >= max_rounds - 1 and not has_converged(current_solutions):
        return {
            "converged": False,
            "reason": "修订轮次超过上限",
            "residual_uncertainty": identify_residual_uncertainty(current_solutions),
            "rounds": rounds
        }
    
    return {
        "converged": True,
        "final_solutions": current_solutions,
        "rounds": rounds
    }
```

### C5 证据加权（Evidence Weighting）

为每条证据分配权重与置信度：

```yaml
evidence_weighting:
  weights:
    - evidence_id: "E1"
      source: "历史诊断数据"
      base_weight: high
      confidence: high
      adjusted_weight: 0.9
      rationale: "数据来自同一系统，高可信度"
    
    - evidence_id: "E2"
      source: "用户反馈"
      base_weight: medium
      confidence: medium
      adjusted_weight: 0.6
      rationale: "样本量有限，可能存在偏差"
    
    - evidence_id: "E3"
      source: "技术文档"
      base_weight: medium
      confidence: high
      adjusted_weight: 0.7
      rationale: "文档可能过时，但来源可靠"
  
  aggregate:
    solution_S1: 0.75
    solution_S2: 0.65
    solution_S3: 0.45
```

### C6 决策产出（Decision Output）

```yaml
council_decision:
  decision_id: "CD001"
  status: accepted | rejected | deferred
  selected_solution: "S1"
  rationale: "<决策理由>"
  
  evidence_weighted_score:
    S1: 0.75
    S2: 0.65
    S3: 0.45
  
  objections:
    - id: "OBJ1"
      raised_by: "red_team"
      description: "方案 S1 的用户升级率假设可能不成立"
      severity: medium
      resolution: "已添加降级方案"
      accepted: true
    
    - id: "OBJ2"
      raised_by: "reviewer_B"
      description: "方案 S1 的测试覆盖不足"
      severity: high
      resolution: "已补充测试计划"
      accepted: true
  
  unresolved_issues:
    - id: "UI1"
      description: "性能指标未完全验证"
      impact: low
      follow_up: "在实施阶段补充性能测试"
  
  next_steps:
    - "进入 plan 阶段"
    - "实施阶段补充性能测试"
  
  decided_at: "<ISO8601>"
  decided_by: "pax-council"
  participants:
    - role: "chair"
      name: "pax-council"
    - role: "red_team"
      name: "anonymous"
    - role: "reviewer"
      name: "anonymous"
```

### C7 异议记录（Objection Record）

```yaml
objection_record:
  - id: "OBJ1"
    objection: "用户升级率假设可能不成立"
    raised_at: "2026-09-29"
    severity: medium
    resolution: "已添加降级方案"
    accepted_by: ["chair", "reviewer_B"]
    rejected_by: []
  
  - id: "OBJ2"
    objection: "测试覆盖不足"
    raised_at: "2026-09-29"
    severity: high
    resolution: "已补充测试计划"
    accepted_by: ["chair", "red_team", "reviewer_B"]
    rejected_by: []
  
  - id: "OBJ3"
    objection: "方案 S2 的迁移成本仍不确定"
    raised_at: "2026-09-29"
    severity: medium
    resolution: "未解决，作为未决问题记录"
    accepted_by: ["chair"]
    rejected_by: ["red_team"]
    status: unresolved
```

## 输出契约
- 证据加权决策（不写入快照，除非主流程主动引用）
- 异议记录（含未支持方案）
- 未解决问题清单

## 失败模式
- 修订轮次超过上限 → 强制收敛并声明残余不确定性
- 证据严重不足 → 声明 `blocked`，列出缺失
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 超出 council 权限或涉及外部合规 → 请求人工审批
- 需要独立验证方案 → `pax-verify`
