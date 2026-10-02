---
name: pax-test
description: >
    Use when: 自动化测试生成。此 skill 由 pax-orchestrate 在编排路由中调用，用于自动生成测试用例并执行测试。
version: 0.2.0
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
        regression_tests = generate_regression_tests(snapshot.diagnosis)
        tests.extend(regression_tests)
    
    return tests
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