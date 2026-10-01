---
name: pax-review
description: >
    Use when: 独立评审门禁，对照成功标准决定通过/拒绝。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 0.2.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-review


## Overview

独立评审门禁。以契约为准独立评估执行结果，判定通过 / 有条件通过 / 拒绝。

## When to Use

执行完成后，进入评审阶段；高风险任务强制经过此 Skill。

## Common Pitfalls

- 与执行阶段同一 Agent 评审，缺乏独立性。
- 只评审结果，未评审过程与审计留痕。
- 拒绝时未给出可执行的修复清单。

## Verification Checklist

- [ ] 评审结论有明确的通过 / 有条件通过 / 拒绝
- [ ] 评审意见包含可执行修复清单并写入快照
- [ ] 评审留痕完整（输入、检查点、结论、时间戳）
## Execution Contract
- 前置门禁：`snapshot.execution` 已产出，`plan.verification_strategy[]` 存在
- 未通过门禁：拒绝启动，返回执行阶段补齐日志
- 版本检查：`pax-ops/versions.json`
- 门禁：`verdict: pass` 才能进入文档沉淀阶段
- 门禁：`verdict: fail` 返回执行阶段
- 门禁：`verdict: escalated` 升级 `pax-council`
- 禁止在缺乏 `pax-verify` 印章时给出 `verdict: pass`

## 职责边界
- 做什么：独立评审门禁，对照成功标准决定通过/拒绝
- 不做什么：不修改执行结果、不重跑执行、不写文档

## 输入
- 必需：`snapshot.execution`、`snapshot.plan`、`snapshot.contract`
- 可选：`snapshot.verify_stamp`

## 工作流

### R1 门禁校验（Gate Check）

```python
def check_gate(snapshot):
    """校验前置门禁"""
    
    if not snapshot.execution:
        return False, "缺少执行结果"
    
    if not snapshot.plan.verification_strategy:
        return False, "缺少验证策略"
    
    if snapshot.execution.status != "completed":
        return False, f"执行状态为 {snapshot.execution.status}，需要 completed"
    
    return True, "门禁通过"
```

### R2 逐项验收（Item-by-Item Verification）

**验收流程**：
1. 读取 `plan.verification_strategy[]`
2. 逐项对照执行结果
3. 记录每项 `pass/fail`
4. 收集证据

```python
def verify_items(plan, execution):
    """逐项验收"""
    
    results = []
    
    for strategy in plan.verification_strategy:
        step = find_step(plan.steps, strategy.step)
        log_entry = find_log(execution.log, strategy.step)
        
        # 检查执行状态
        if not log_entry or log_entry.result != "success":
            results.append({
                "step": strategy.step,
                "method": strategy.method,
                "criteria": strategy.criteria,
                "result": "fail",
                "reason": "步骤未成功执行",
                "evidence": None
            })
            continue
        
        # 执行验证方法
        evidence = execute_verification(strategy, step, log_entry)
        
        # 判定结果
        result = evaluate_criteria(strategy.criteria, evidence)
        
        results.append({
            "step": strategy.step,
            "method": strategy.method,
            "criteria": strategy.criteria,
            "result": result,  # pass | fail
            "reason": evaluate_rationale(strategy, evidence),
            "evidence": evidence
        })
    
    return results
```

**验证方法**：

| 方法 | 验证内容 | 证据 |
|------|----------|------|
| `unit_test` | 单元测试结果 | 测试报告 |
| `code_review` | 代码审查结果 | Review comments |
| `data_validation` | 数据一致性检查 | 查询结果 |
| `integration_test` | 集成测试结果 | 测试报告 |
| `manual_check` | 手动检查 | 检查记录 |

### R3 偏差检查（Deviation Check）

检查 `execution.deviations[]` 是否已处理：

```python
def check_deviations(execution):
    """检查偏差"""
    
    issues = []
    
    for deviation in execution.deviations:
        # 检查 high 偏差是否已解决
        if deviation.severity == "high" and not deviation.resolved:
            issues.append({
                "deviation": deviation,
                "issue": "high 偏差未解决"
            })
        
        # 检查 medium 偏差是否已报告
        if deviation.severity == "medium" and not deviation.resolved:
            issues.append({
                "deviation": deviation,
                "issue": "medium 偏差未解决"
            })
    
    return issues
```

### R4 印章检查（Stamp Check）

检查 `pax-verify` 印章：

```python
def check_stamp(snapshot):
    """检查 pax-verify 印章"""
    
    if not snapshot.verify_stamp:
        return False, "缺少 pax-verify 印章"
    
    if snapshot.verify_stamp.result not in ("pass", "partial"):
        return False, f"印章结果为 {snapshot.verify_stamp.result}，需要 pass 或 partial"
    
    # 检查印章证据
    if not snapshot.verify_stamp.evidence:
        return False, "印章缺少证据"
    
    return True, None
```

### R5 综合判定（Comprehensive Verdict）

```python
def determine_verdict(verification_results, deviations, stamp):
    """综合判定 verdict"""
    
    # 条件 1: 印章缺失
    if not stamp.valid:
        return "blocked", "缺少 pax-verify 印章"
    
    # 条件 2: high 偏差未解决
    unresolved_high = [
        d for d in deviations 
        if d.severity == "high" and not d.resolved
    ]
    if unresolved_high:
        return "fail", f"存在 {len(unresolved_high)} 个未解决的 high 偏差"
    
    # 条件 3: 验收结果
    all_pass = all(r.result == "pass" for r in verification_results)
    some_fail = any(r.result == "fail" for r in verification_results)
    some_partial = any(
        r.result == "fail" and 
        should_allow_deferral(r) 
        for r in verification_results
    )
    
    if all_pass:
        return "pass", "全部验收项通过"
    
    if some_fail and not some_partial:
        return "fail", "存在未通过的验收项"
    
    if some_partial:
        return "partial", "部分通过，允许延期"
    
    # 条件 4: 超出评审权限
    if exceeds_review_authority():
        return "escalated", "超出评审权限"
    
    return "blocked", "证据不足"
```

### R6 评审结论（Review Conclusion）

**五态 verdict**：

| verdict | 语义 | 后续 |
|---------|------|------|
| `pass` | 全部通过 | 进入文档沉淀 |
| `fail` | 存在未通过项 | 返回执行阶段 |
| `partial` | 部分通过，允许延期 | 记录待办，进入文档草稿 |
| `blocked` | 证据或印章缺失 | 返回执行/验证阶段 |
| `escalated` | 超出评审权限 | 升级 `pax-council` |

**Finding 分类**：

| 严重度 | 条件 | 处理 |
|--------|------|------|
| `blocker` | 阻塞发布 | 必须修复，`verdict: fail` |
| `major` | 影响功能 | 建议修复，可 `partial` |
| `minor` | 不影响功能 | 记录待办 |
| `info` | 信息性 | 仅记录 |

**输出格式**：
```yaml
review:
  verdict: pass | fail | partial | blocked | escalated
  stamp: "<唯一标识>"
  rationale: "<判定理由>"
  findings:
    - id: F1
      severity: blocker | major | minor | info
      step: S1
      description: "<发现描述>"
      evidence: "<证据>"
      recommendation: "<建议>"
    - id: F2
      severity: major
      step: S2
      description: "<发现描述>"
      evidence: "<证据>"
      recommendation: "<建议>"
  verification_results:
    - step: S1
      method: unit_test
      criteria: "所有测试通过"
      result: pass
      evidence: "10/10 tests passed"
    - step: S2
      method: code_review
      criteria: "无阻塞性问题"
      result: pass
      evidence: "Review comments addressed"
  deviations_check:
    total: 2
    resolved: 2
    unresolved: 0
    high_unresolved: 0
  stamp_check:
    valid: true
    result: pass
    confidence: high
  reviewed_at: "<ISO8601>"
  reviewed_by: "pax-review"
```

## 输出契约
- `snapshot.review`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- `pax-verify` 印章缺失 → `verdict: blocked`
- 与契约偏差未处理 → `verdict: fail`
- 超出评审权限 → `verdict: escalated`

## 何时升级
- `verdict: pass` → 进入文档沉淀阶段
- `verdict: fail` → 返回执行阶段
- `verdict: escalated` → `pax-council`
- 需要独立验证 → `pax-verify`
