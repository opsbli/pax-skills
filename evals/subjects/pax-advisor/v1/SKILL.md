---
name: pax-advisor
description: >
    Use when: 只读顾问，针对特定假设、权衡、架构问题提供咨询。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 0.2.0
family: pax
layer: L2
optional: true
requires_snapshot: true
---

# pax-advisor


## Overview

单点咨询 Skill。针对一个具体问题给出建议，不改动任何状态。

## When to Use

用户或上层 Agent 想要一个专家观点，但不希望触发完整执行流程。

## Common Pitfalls

- 建议过宽泛，缺乏可执行性。
- 越界触发本应交给多专家盲审的决策。
- 未留下建议留痕。

## Verification Checklist

- [ ] 建议针对单一问题，边界清晰
- [ ] 建议附有依据与不确定性说明
- [ ] 建议留痕写入快照，可以追溯
## Execution Contract
- 前置门禁：需要完整快照或明确的问题陈述
- 未通过门禁：拒绝启动，返回用户补齐上下文
- 版本检查：`pax-ops/versions.json`
- 只读：不修改快照、不改变主流程、不认领路由落点
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：针对特定假设、权衡、架构问题提供咨询意见
- 不做什么：不修改快照、不改变主流程、不认领路由落点、不产出可冻结契约

## 输入
- 必需：完整快照或明确的咨询问题
- 可选：上下文材料、历史决策、候选方案清单

## 工作流

### A1 咨询焦点识别（Focus Identification）

```python
def identify_focus(input):
    """识别咨询焦点"""
    
    if input.has_snapshot:
        # 从快照推断焦点
        if input.snapshot.diagnosis and not input.snapshot.plan:
            return "diagnosis_review"  # 诊断结论审核
        elif input.snapshot.plan and not input.snapshot.execution:
            return "plan_review"  # 计划审核
        elif input.snapshot.execution and not input.snapshot.review:
            return "execution_review"  # 执行审核
        else:
            return "general"  # 一般咨询
    elif input.question:
        # 从问题推断焦点
        if "权衡" in input.question or "tradeoff" in input.question:
            return "tradeoff"
        elif "架构" in input.question or "architecture" in input.question:
            return "architecture"
        elif "方案" in input.question or "option" in input.question:
            return "options"
        else:
            return "general"
    else:
        return "blocked"  # 信息不足
```

### A2 候选方案生成（Candidate Generation）

至少 2 个候选方案：

```yaml
candidate_options:
  - id: "O1"
    name: "<方案名称>"
    description: "<方案描述>"
    approach: "<实现方法>"
    
    pros:
      - "<优点 1>"
      - "<优点 2>"
    
    cons:
      - "<缺点 1>"
      - "<缺点 2>"
    
    evidence:
      - source: "<证据来源>"
        content: "<证据内容>"
        weight: high | medium | low
    
    risks:
      - type: technical | operational | business
        description: "<风险描述>"
        probability: high | medium | low
        impact: high | medium | low
    
    costs:
      - type: time | money | resources
        estimate: "<成本估计>"
        uncertainty: high | medium | low
    
    dependencies:
      - "<依赖项>"
    
  - id: "O2"
    ...
```

### A3 证据加权评估（Evidence-Weighted Evaluation）

```python
def evaluate_options(options):
    """证据加权评估"""
    
    evaluations = []
    
    for option in options:
        # 计算证据权重
        evidence_score = calculate_evidence_score(option.evidence)
        
        # 计算风险分数
        risk_score = calculate_risk_score(option.risks)
        
        # 计算成本分数
        cost_score = calculate_cost_score(option.costs)
        
        # 计算综合分数
        composite_score = (
            evidence_score * 0.4 +
            (1 - risk_score) * 0.3 +
            (1 - cost_score) * 0.3
        )
        
        evaluation = {
            "option_id": option.id,
            "evidence_score": evidence_score,
            "risk_score": risk_score,
            "cost_score": cost_score,
            "composite_score": composite_score,
            "support_level": determine_support_level(composite_score),
            "confidence": determine_confidence(option)
        }
        evaluations.append(evaluation)
    
    # 排序
    evaluations.sort(key=lambda e: e["composite_score"], reverse=True)
    
    return evaluations
```

**评分标准**：

| 分数范围 | 支持度 | 建议 |
|----------|--------|------|
| 0.8-1.0 | strong | 强烈推荐 |
| 0.6-0.8 | moderate | 推荐 |
| 0.4-0.6 | weak | 可选 |
| 0.2-0.4 | weak | 不推荐 |
| 0.0-0.2 | none | 不推荐 |

### A4 异议记录（Objection Recording）

```yaml
objections:
  - id: "OBJ1"
    option: "O1"
    type: assumption | risk | cost | dependency
    description: "<异议描述>"
    severity: high | medium | low
    raised_by: "advisor"
    resolution: addressed | partially_addressed | unresolved
    mitigation: "<缓解措施>"
  
  - id: "OBJ2"
    option: "O2"
    type: risk
    description: "<异议描述>"
    severity: medium
    raised_by: "advisor"
    resolution: unresolved
    mitigation: "无有效缓解措施"
```

### A5 咨询意见输出（Consultation Output）

```yaml
consultation:
  focus: "tradeoff" | "architecture" | "options" | "general"
  question: "<咨询问题>"
  
  options_evaluated:
    - id: "O1"
      name: "<方案名称>"
      composite_score: 0.85
      support_level: strong
      confidence: high
    - id: "O2"
      name: "<方案名称>"
      composite_score: 0.65
      support_level: moderate
      confidence: medium
  
  recommendation:
    primary: "O1"
    rationale: "<推荐理由>"
    conditions:
      - "<使用条件>"
    alternatives:
      - id: "O2"
        when_to_consider: "<何时考虑替代方案>"
  
  objections:
    - id: "OBJ1"
      description: "<异议描述>"
      resolution: addressed
  
  tradeoffs:
    - dimension: "performance"
      option_O1: "high"
      option_O2: "medium"
      impact: "O1 性能更好，但实现复杂"
    - dimension: "maintainability"
      option_O1: "medium"
      option_O2: "high"
      impact: "O2 更易于维护"
  
  uncertainties:
    - description: "<不确定性描述>"
      impact: high | medium | low
      mitigation: "<缓解措施>"
  
  metadata:
    advisor: "pax-advisor"
    timestamp: "<ISO8601>"
    read_only: true
    snapshot_modified: false
```

### A6 失败处理（Failure Handling）

```python
def handle_failure(input):
    """处理失败"""
    
    # 条件 1: 信息不足
    if not input.has_snapshot and not input.question:
        return {
            "status": "blocked",
            "missing": ["snapshot 或明确的问题陈述"],
            "recommendation": "请提供完整快照或明确咨询问题"
        }
    
    # 条件 2: 只存在单一候选
    if len(input.candidates) == 1:
        return {
            "status": "partial",
            "reason": "只存在单一候选方案",
            "recommendation": input.candidates[0],
            "uncertainty": "无法进行对比评估，建议补充替代方案"
        }
    
    # 条件 3: 证据严重不足
    if calculate_evidence_score(input.evidence) < 0.3:
        return {
            "status": "partial",
            "reason": "证据严重不足",
            "recommendation": None,
            "uncertainty": "无法做出可靠推荐"
        }
    
    return None  # 正常执行
```

## 输出契约
- 咨询意见文本（不写入快照）
- 可选附带：候选方案表、证据权重、异议清单

## 失败模式
- 信息不足 → 声明 `blocked` 并列出缺失
- 只存在单一候选 → 声明 `partial`，附推荐与不确定性
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 高风险或跨系统决策 → 转多层盲审机制处理
- 需要独立验证 → `pax-verify`
