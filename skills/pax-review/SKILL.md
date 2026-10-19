---
name: pax-review
description: >
    Use when: 独立评审门禁，对照成功标准决定通过/拒绝。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 1.0.2
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
- 门禁：`verdict: verified` 才能进入文档沉淀阶段
- 门禁：`verdict: needs_fix` 返回执行阶段
- 门禁：`verdict: needs_review` 升级 `pax-council`
- 禁止在缺乏 `pax-verify` 印章时给出 `verdict: verified`

## 职责边界
- 做什么：独立评审门禁，对照成功标准决定通过/拒绝
- 不做什么：不修改执行结果、不重跑执行、不写文档

## 输入
- 必需：`snapshot.execution`、`snapshot.plan`、`snapshot.contract`
- 可选：`snapshot.quality.verification_seals`（pax-verify 与门禁段的印章序列，取最后一条；
  若末条来自门禁段且 `result: blocked`，则评审应判拒绝）

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

    if getattr(snapshot, "execution_status", None):
        return False, "禁止用 execution_status 替代标准 execution"

    pending = [
        item for item in snapshot.execution.log
        if getattr(item, "manual", None) == "pending" or "pending" in str(getattr(item, "evidence", ""))
    ]
    if pending:
        return False, "存在 pending 手动验证，不能评审通过"
    
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
                "result": "needs_fix",
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
            "result": result,  # verified | needs_fix | partial
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

### R2.5 PIE 完整性检查（PIE Completeness Check）

读取 `snapshot.tests.pie_check[]`，按下列规则判定 PIE 完整性，作为 `verdict` 计算前的独立门禁。

```python
def check_pie_completeness(snapshot):
    """PIE 完整性检查，返回 (ok, reason, findings)"""

    findings = []
    pie_checks = snapshot.tests.pie_check if snapshot.tests else []

    if not pie_checks:
        return False, "缺少 PIE 自检结果", [
            {"severity": "major", "description": "T1.5 未运行，无法评估测试有效性"}
        ]

    # 检查是否存在 execution=fail 的用例
    exec_fails = [c for c in pie_checks if c.execution == "fail"]
    if exec_fails:
        findings.append({
            "severity": "major",
            "description": f"{len(exec_fails)} 条用例未覆盖目标路径",
            "test_ids": [c.test_id for c in exec_fails],
        })

    # 检查是否存在 propagation=fail 的用例
    prop_fails = [c for c in pie_checks if c.propagation == "fail"]
    if prop_fails:
        findings.append({
            "severity": "major",
            "description": f"{len(prop_fails)} 条用例断言不足以观察到错误",
            "test_ids": [c.test_id for c in prop_fails],
        })

    # 输入不是运行时会产生的值（含从被测字符串回抄）也是 major，不能只留在 recommendations
    infection_fails = [c for c in pie_checks if c.infection == "fail"]
    if infection_fails:
        findings.append({
            "severity": "major",
            "description": f"{len(infection_fails)} 条用例输入不能触发错误状态或不是运行时事件",
            "test_ids": [c.test_id for c in infection_fails],
        })

    # 检查 n/a 比例
    na_ratio = sum(1 for c in pie_checks if c.execution == "n/a") / len(pie_checks)
    if na_ratio > 0.5:
        findings.append({
            "severity": "minor",
            "description": f"{na_ratio:.0%} 用例被标记为 n/a，超过 50% 上限，需说明理由"
        })

    has_major = any(f.severity == "major" for f in findings)
    return (not has_major), None, findings
```

**门禁规则**：
- 存在 `severity == "major"` 的 PIE 发现 → `verdict` 不得为 `verified`，最低为 `needs_fix`；
- 只有 `severity == "minor"` 的发现 → `verdict` 可给 `partial`，但需在 `rationale` 里显式引用；
- `pie_check[]` 缺失 → `verdict: blocked`，回到测试生成阶段补跑 T1.5。

### R2.6 行为等价性断言（Behavior Equivalence Assertion，支撑重构类任务）

当 `intent.primary == "refactor"`（或路由标注重构）时，除结构正确性外，评审还必须断言
**重构前后行为等价**——这是重构类任务通过评审的必要条件。

```python
def check_behavior_equivalence(snapshot):
    """重构类任务的行为等价性断言。

    判据：重构前后对外可观察行为保持一致。以下任一项缺失/不满足 → 存在
    major 等价性风险，verdict 不得为 verified。
    """
    findings = []
    goals = snapshot.goal or {}
    plans = snapshot.plan or {}
    tests = snapshot.tests or {}
    ctrs = snapshot.contract or {}
    if not goals or not plans:
        return False, "缺少 goal/plan，无法界定行为面", []

    # 1) 行为面覆盖：重构必须明确覆盖到哪些对外行为（接口、输入输出、错误码、边界）
    behavior_surface = (goals.get("success_criteria")
                        or plans.get("verification_strategy")
                        or [])
    if not behavior_surface:
        findings.append({
            "severity": "major",
            "description": "重构未声明行为面（接口/输入输出/错误码/边界），无法证明等价"
        })

    # 2) 回归证据：必须存在重构后对新行为面的自动化回归（测试或契约校验）
    pie = tests.get("pie_check") if isinstance(tests, dict) else []
    pie = pie or []
    has_regression = any(
        t.get("behavior_equivalent") is True for t in pie
    ) if isinstance(pie, list) else False
    if not has_regression:
        findings.append({
            "severity": "major",
            "description": "缺少重构后行为等价回归证据（behavior_equivalent=true 未出现）"
        })

    # 3) 外部契约不变：快照 contract 段在重构前后不应被破坏性变更（除非显式声明）
    if ctrs and ctrs.get("breaking") is True:
        findings.append({
            "severity": "major",
            "description": "重构引入破坏性契约变更，需用户显式确认"
        })

    has_major = any(f["severity"] == "major" for f in findings)
    return (not has_major), None, findings
```

**门禁规则**：
- 重构类任务：存在 `major` 行为等价性发现 → `verdict` 不得为 `verified`，最低 `needs_fix`；
- 行为面未声明 或 缺等价回归 或 破坏性契约未确认 → 均判 `major`。

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
    """只有 D3/交互步骤强制 pax-verify 印章。纯文档缺印章不 blocked。"""

    required = getattr(snapshot.plan, "requires_runtime_verification", False)
    seals = snapshot.quality.verification_seals if snapshot.quality else []
    if not required:
        return True, None
    if not seals:
        return False, "D3/交互步骤缺少 pax-verify 印章"
    
    seal = seals[-1]
    if seal.result not in ("verified", "partial"):
        return False, f"印章结果为 {seal.result}，需要 verified 或 partial"
    
    # 检查印章证据
    if not seal.evidence:
        return False, "印章缺少证据"
    
    return True, None
```

### R5 综合判定（Comprehensive Verdict）

```python
def runtime_verification_gap(snapshot):
    """D3/交互步骤缺测试、验证或手动观察时，不能 verified，也不能 partial。"""
    plan = snapshot.plan
    if not getattr(plan, "requires_runtime_verification", False):
        return []
    missing = []
    pie = snapshot.tests.pie_check if getattr(snapshot, "tests", None) else []
    if not pie:
        missing.append("pax-test.pie_check")
    step_ids = set(getattr(plan, "runtime_verification_steps", []) or [])
    logs = [item for item in snapshot.execution.log if item.step in step_ids]
    if not logs or not all(evidence_includes_manual(item) for item in logs):
        missing.append("manual_evidence")
    return missing

def determine_verdict(snapshot, verification_results, deviations, stamp):
    """综合判定 verdict（stamp 为 check_stamp 的返回 `(ok, reason)`）"""

    stamp_ok, stamp_reason = stamp
    if not stamp_ok:
        return "blocked", stamp_reason
    gap = runtime_verification_gap(snapshot)
    if gap:
        return "blocked", f"D3/交互步骤缺少 {', '.join(gap)}，不能 verified 或 partial"
    
    # 条件 2: high 偏差未解决
    unresolved_high = [
        d for d in deviations 
        if d.severity == "high" and not d.resolved
    ]
    if unresolved_high:
        return "needs_fix", f"存在 {len(unresolved_high)} 个未解决的 high 偏差"
    
    # 条件 3: 验收结果
    all_pass = all(r.result == "verified" for r in verification_results)
    some_fail = any(r.result == "needs_fix" for r in verification_results)
    some_partial = any(
        r.result == "needs_fix" and 
        should_allow_deferral(r) 
        for r in verification_results
    )
    
    if all_pass:
        return "verified", "全部验收项通过"
    
    if some_fail and not some_partial:
        return "needs_fix", "存在未通过的验收项"
    
    if some_partial:
        return "partial", "部分通过，允许延期"
    
    # 条件 4: 超出评审权限
    if exceeds_review_authority():
        return "needs_review", "超出评审权限"
    
    return "blocked", "证据不足"
```

### R6 评审结论（Review Conclusion）

**五态 verdict**：

| verdict | 语义 | 后续 |
|---------|------|------|
| `verified` | 全部通过 | 进入文档沉淀 |
| `needs_fix` | 存在未通过项 | 返回执行阶段 |
| `partial` | 部分通过，允许延期 | 记录待办，进入文档草稿 |
| `blocked` | 证据或印章缺失 | 返回执行/验证阶段 |
| `needs_review` | 超出评审权限 | 升级 `pax-council` |

**Finding 分类**：

| 严重度 | 条件 | 处理 |
|--------|------|------|
| `blocker` | 阻塞发布 | 必须修复，`verdict: needs_fix` |
| `major` | 影响功能 | D3/交互未接通时不得延期为 `partial`，verdict 为 `blocked` 或 `needs_fix` |
| `minor` | 不影响功能 | 记录待办 |
| `info` | 信息性 | 仅记录 |

**输出格式**：
```yaml
review:
  verdict: verified | needs_fix | partial | blocked | needs_review
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
      evidence: "10/10 tests passed。该步骤若是 D3，只有这一条则 verdict 仍是 blocked"
    - step: S3
      method: manual_check
      criteria: "快捷键生效"
      result: pass
      evidence: "environment: tauri dev; action: Ctrl+N; observed_result: 出现未命名文档; at: 2026-10-15T15:00:00+08:00"
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

### R6.5 发布门禁联动（pax-gate，L1→L1）

涉及发布 / 新增依赖 / 数据采集 / 安全敏感的改动，评审在给出 `verified` 前应调用 `pax-gate`
（发布前质量门禁：SAST / 密钥 / 依赖漏洞 / 合规 / 可访问性 / 许可证）作为前置门禁：

- `pax-gate` 产出 `snapshot.quality.verification_seals`（五态 + 证据 + 置信度，fail-closed）。
- 任一 `critical` / `high` 封印 → 阻断 `verified`，`verdict` 最低 `needs_fix`。
- 纯文档 / 无发布面改动可跳过（记 `skip_reason`）。

## 输出契约
- `snapshot.review`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- D3/交互步骤缺少 `pax-test` 的 `pie_check`、`pax-verify` 印章或手动观察 → `verdict: blocked`，不能是 `verified` 或 `partial`
- 非 D3 任务不因缺少 `pax-verify` 印章而 `blocked`
- 与契约偏差未处理 → `verdict: needs_fix`
- 超出评审权限 → `verdict: needs_review`

## 何时升级
- `verdict: verified` → 进入文档沉淀阶段
- `verdict: needs_fix` → 返回执行阶段
- `verdict: needs_review` → `pax-council`
- 需要独立验证 → `pax-verify`
