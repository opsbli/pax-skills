---
name: pax-test
description: >
    Use when: 自动化测试生成。此 skill 由 pax-orchestrate 在编排路由中调用，用于自动生成测试用例并执行测试。
version: 1.0.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-test


## Overview

自动化测试生成 Skill。根据代码 / 契约生成测试用例，覆盖率不达标时补测。

## When to Use

新功能开发完成、契约变更后、或评审要求补测时。

## Common Pitfalls

- 生成的测试用例覆盖不到边界条件。
- 只测正向路径。
- 未与 CI 集成。

## Verification Checklist

- [ ] 测试覆盖正向 / 反向 / 边界三类路径
- [ ] 测试可在 CI 中稳定执行
- [ ] 覆盖率与验收标准对齐
- [ ] 每条测试用例通过 PIE 三问自检（T1.5），或显式声明 `pie_check.rationale` 说明为何允许部分为 `n/a`
- [ ] 关键业务字段与副作用（DB / 缓存 / 日志 / 消息 / 下游接口）已纳入断言（对应 PIE 的 Propagation）
## Execution Contract
- 前置门禁：`snapshot.plan.status == frozen` 且 `snapshot.plan.steps` 存在
- 未通过门禁：拒绝启动，返回规划阶段
- 版本检查：`pax-ops/versions.json`
- skip_reason：当风险等级为 low 且任务类型为 doc_consult 时可跳过
- 禁止在测试未通过时标记任务完成
- 禁止跳过测试步骤

## 职责边界
- 做什么：生成测试用例、执行测试、报告测试结果
- 不做什么：不修复代码、不做诊断、不规划任务

## 输入
- 必需：`snapshot.plan`、`snapshot.execution`
- 可选：测试配置、测试框架

## 工作流

### T1 测试生成（Test Generation）

```python
def generate_tests(snapshot):
    """生成测试用例"""
    
    tests = []
    
    # 根据步骤类型生成测试
    for step in snapshot.plan.steps:
        step_tests = generate_tests_for_step(step)
        tests.extend(step_tests)
    
    # 生成集成测试
    integration_tests = generate_integration_tests(snapshot)
    tests.extend(integration_tests)
    
    # 生成回归测试（诊断类任务）
    if snapshot.orchestration.diagnose_required:
        regression_tests = generate_regression_tests(
            snapshot.diagnosis,
            strategy=snapshot.diagnosis.root_cause.regression_scope_strategy,
        )
        tests.extend(regression_tests)
    
    return tests
```

**按策略分档生成回归用例**（由 `diagnosis.root_cause.regression_scope_strategy` 驱动）：

```python
def generate_regression_tests(diagnosis, strategy):
    """按策略分档生成回归用例。strategy 取自 diagnosis.root_cause.regression_scope_strategy。"""
    scope_items = diagnosis.root_cause.regression_scope   # 数组结构保持不变

    if strategy == "full":
        # 全量：生成所有模块的回归用例，无过滤
        return _generate_for_all_modules(scope_items)

    if strategy == "selective":
        # 选择性：只生成 must_test + should_test
        return _generate_for_modules(
            [m for m in scope_items if m.priority in ("must_test", "should_test")]
        )

    if strategy == "priority":
        # 优先级：只生成 must_test，加最多 20% 的 should_test
        must = [m for m in scope_items if m.priority == "must_test"]
        should = [m for m in scope_items if m.priority == "should_test"]
        sampled_should = should[: max(1, len(should) // 5)]
        return _generate_for_modules(must + sampled_should)

    # 未声明策略时回退为 priority 行为（宁可少测，不可多测无用功）
    return _generate_for_modules(
        [m for m in scope_items if m.priority == "must_test"]
    )
```

**步骤测试生成**：
```python
def generate_tests_for_step(step):
    """为步骤生成测试"""
    
    tests = []
    step_id = step["id"]
    step_action = step["action"]
    
    # 根据步骤类型生成测试
    if "实现" in step_action or "开发" in step_action:
        tests.append({
            "id": f"{step_id}_unit",
            "type": "unit",
            "description": f"单元测试: {step_action}",
            "coverage_target": 80,
            "test_cases": generate_unit_test_cases(step)
        })
    
    if "接口" in step_action or "API" in step_action:
        tests.append({
            "id": f"{step_id}_api",
            "type": "api",
            "description": f"API 测试: {step_action}",
            "test_cases": generate_api_test_cases(step)
        })
    
    if "数据" in step_action or "订正" in step_action:
        tests.append({
            "id": f"{step_id}_data",
            "type": "data",
            "description": f"数据测试: {step_action}",
            "test_cases": generate_data_test_cases(step)
        })
    
    return tests
```

### T1.5 PIE 自检（PIE Self-Check）

每条测试用例在进入 T2 执行前，必须回答三问，并把结论写入 `snapshot.tests.pie_check[]`。

| 问 | 关键判据 | `fail` 信号 |
|---|---|---|
| **E**（Execution）：是否执行到可能出错的代码路径？ | 覆盖目标分支、异常分支或修改点 | 覆盖率报告显示未触达修改 diff 中的路径 |
| **I**（Infection）：输入是否会让错误状态在内部产生？ | 使用边界值 / 等价类外值 / 敏感输入组合 | 输入全是"正常值"，未包含边界、非法、极端值 |
| **P**（Propagation）：断言是否能观察到错误？ | 检查关键业务字段 + 副作用（DB / 缓存 / 日志 / 消息 / 下游接口） | 只调用函数无断言；只检查 `success: true`；不查数据库写入 |

```python
def check_pie(test_case):
    """对单条测试用例做 PIE 自检"""

    # E：目标路径被执行
    execution = "pass" if test_case.touched_target_path else "fail"

    # I：输入能触发错误状态
    infection = "pass" if has_sensitive_input(test_case.inputs) else "fail"

    # P：断言能观察到错误
    propagation = (
        "pass"
        if test_case.assertions
        and checks_key_business_fields(test_case.assertions)
        and checks_side_effects(test_case.assertions)
        else "fail"
    )

    return {
        "test_id": test_case.id,
        "execution": execution,
        "infection": infection,
        "propagation": propagation,
        "rationale": summarize_pie(test_case),
    }
```

**跳过留痕**：用例若声明 `pie_check.rationale` 说明该用例是纯回归 smoke（只求"没崩"），可将 `execution / infection / propagation` 全部置 `n/a`；但同一 step 内 `n/a` 比例不得高于 50%。

**门禁**：
- 任何 `execution == fail` 的用例必须补测后才能进入 T2；
- `propagation == fail` 的用例必须在 T2 前补断言；
- `infection == fail` 的用例需在 T4 报告的 `recommendations` 中标注"用例敏感度不足"。

**T4 报告追加**：`generate_test_report` 输出的 `report` 增加 `pie_summary` 段，统计本次执行中 `E / I / P` 三项的通过率，与覆盖率并列展示。

### T2 测试执行（Test Execution）

```python
def execute_tests(tests, config):
    """执行测试"""
    
    results = {
        "status": "pending",
        "started_at": "<ISO8601>",
        "config": config,
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
    }
    
    for test in tests:
        result = execute_test(test)
        results["tests"].append(result)
        
        # 更新统计
        results["summary"]["total"] += 1
        if result["status"] == "passed":
            results["summary"]["passed"] += 1
        elif result["status"] == "failed":
            results["summary"]["failed"] += 1
        else:
            results["summary"]["skipped"] += 1
    
    results["completed_at"] = "<ISO8601>"
    results["status"] = "passed" if results["summary"]["failed"] == 0 else "failed"
    
    return results
```

**执行单个测试**：
```python
def execute_test(test):
    """执行单个测试"""
    
    result = {
        "test_id": test["id"],
        "type": test["type"],
        "description": test["description"],
        "status": "pending",
        "started_at": "<ISO8601>",
        "test_cases": []
    }
    
    for case in test["test_cases"]:
        case_result = execute_test_case(case)
        result["test_cases"].append(case_result)
    
    # 汇总测试用例结果
    passed = sum(1 for c in result["test_cases"] if c["status"] == "passed")
    failed = sum(1 for c in result["test_cases"] if c["status"] == "failed")
    
    result["status"] = "passed" if failed == 0 else "failed"
    result["completed_at"] = "<ISO8601>"
    
    return result
```

### T3 覆盖率分析（Coverage Analysis）

```python
def analyze_coverage(test_results, coverage_target):
    """分析覆盖率"""
    
    coverage = {
        "target": coverage_target,
        "actual": 0,
        "status": "pending"
    }
    
    # 计算覆盖率
    if test_results["summary"]["total"] > 0:
        coverage["actual"] = (test_results["summary"]["passed"] / test_results["summary"]["total"]) * 100
        coverage["actual"] = round(coverage["actual"], 2)
    
    # 判断是否达标
    coverage["status"] = "passed" if coverage["actual"] >= coverage_target else "failed"
    
    return coverage
```

### T4 测试报告（Test Report）

```python
def generate_test_report(test_results, coverage):
    """生成测试报告"""
    
    report = {
        "status": test_results["status"],
        "started_at": test_results["started_at"],
        "completed_at": test_results["completed_at"],
        "duration": calculate_duration(test_results["started_at"], test_results["completed_at"]),
        "summary": test_results["summary"],
        "coverage": coverage,
        "failed_tests": [
            t for t in test_results["tests"] 
            if t["status"] == "failed"
        ],
        "recommendations": generate_recommendations(test_results, coverage)
    }
    
    return report
```

**生成建议**：
```python
def generate_recommendations(test_results, coverage):
    """生成建议"""
    
    recommendations = []
    
    # 覆盖率建议
    if coverage["status"] == "failed":
        recommendations.append({
            "type": "coverage",
            "message": f"覆盖率 {coverage['actual']}% 未达标（目标 {coverage['target']}%）",
            "action": "增加测试用例"
        })
    
    # 失败测试建议
    for failed_test in test_results["failed_tests"]:
        recommendations.append({
            "type": "test_failure",
            "message": f"测试 {failed_test['id']} 失败",
            "action": "修复代码或更新测试"
        })
    
    # 性能建议
    if test_results["duration"] > 300:  # 5 分钟
        recommendations.append({
            "type": "performance",
            "message": "测试执行时间较长",
            "action": "优化测试或并行执行"
        })
    
    return recommendations
```

## 输出契约
- `snapshot.tests`（`status` / `summary` / `coverage` / `failed_tests` / `recommendations`）
- 测试报告文件，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 测试生成失败 → 降级为手动测试，标注 `manual: true`
- 测试执行失败 → 标记 `status: failed`，记录失败原因
- 覆盖率不达标 → 标记 `coverage.status: failed`，建议增加测试

## 何时升级
- 测试失败 → `pax-execute`
- 覆盖率不达标 → `pax-plan`
- 需要用户确认 → 返回上游阶段