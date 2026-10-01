---
name: pax-deploy
description: >
  部署流程编排。此 skill 由 pax-orchestrate 在编排路由中调用，用于自动化部署流程。
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-deploy

## Execution Contract
- 前置门禁：`snapshot.plan.status == frozen` 且 `snapshot.execution.status == completed`
- 未通过门禁：拒绝启动，返回执行阶段
- 版本检查：`pax-ops/versions.json`
- skip_reason：当风险等级为 low 且任务类型为 doc_consult 时可跳过
- 禁止在部署过程中修改代码
- 禁止在未确认部署方案时执行部署

## 职责边界
- 做什么：编排部署流程、执行部署步骤、验证部署结果
- 不做什么：不修改代码、不做诊断、不规划任务

## 输入
- 必需：`snapshot.plan`、`snapshot.execution`
- 可选：部署配置、环境配置

## 工作流

### D1 部署准备（Deployment Preparation）

```python
def prepare_deployment(snapshot, config):
    """准备部署"""
    
    deployment = {
        "status": "preparing",
        "started_at": "<ISO8601>",
        "config": {
            "environment": config.get("environment", "staging"),
            "strategy": config.get("strategy", "rolling"),
            "rollback_enabled": config.get("rollback_enabled", True),
            "health_check": config.get("health_check", True)
        },
        "pre_checks": [],
        "post_checks": []
    }
    
    return deployment
```

### D2 前置检查（Pre-Deployment Checks）

```python
def run_pre_checks(snapshot, config):
    """运行前置检查"""
    
    checks = []
    
    # 检查 1: 代码已合并
    check = check_code_merged(snapshot)
    checks.append({
        "id": "code_merged",
        "description": "代码已合并到主分支",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 2: 测试已通过
    check = check_tests_passed(snapshot)
    checks.append({
        "id": "tests_passed",
        "description": "所有测试通过",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 3: 文档已更新
    check = check_docs_updated(snapshot)
    checks.append({
        "id": "docs_updated",
        "description": "文档已更新",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 4: 配置已准备
    check = check_config_ready(config)
    checks.append({
        "id": "config_ready",
        "description": "配置已准备",
        "status": check["status"],
        "details": check["details"]
    })
    
    all_passed = all(c["status"] == "pass" for c in checks)
    
    return {
        "status": "passed" if all_passed else "failed",
        "checks": checks
    }
```

### D3 部署执行（Deployment Execution）

```python
def execute_deployment(snapshot, config):
    """执行部署"""
    
    deployment = {
        "status": "deploying",
        "started_at": "<ISO8601>",
        "strategy": config["strategy"],
        "environment": config["environment"],
        "steps": []
    }
    
    # 根据策略执行部署
    if config["strategy"] == "rolling":
        steps = execute_rolling_deployment(snapshot, config)
    elif config["strategy"] == "blue_green":
        steps = execute_blue_green_deployment(snapshot, config)
    elif config["strategy"] == "canary":
        steps = execute_canary_deployment(snapshot, config)
    else:
        steps = execute_rolling_deployment(snapshot, config)
    
    deployment["steps"] = steps
    deployment["completed_at"] = "<ISO8601>"
    
    return deployment
```

**滚动部署**：
```python
def execute_rolling_deployment(snapshot, config):
    """执行滚动部署"""
    
    steps = []
    total_instances = config.get("instances", 1)
    
    for i in range(total_instances):
        step = {
            "id": f"instance_{i}",
            "type": "rolling_update",
            "instance": i,
            "status": "pending",
            "started_at": "<ISO8601>"
        }
        
        # 执行部署
        result = deploy_to_instance(i, config)
        
        if result.success:
            step["status"] = "completed"
        else:
            step["status"] = "failed"
            step["error"] = result.error
        
        step["completed_at"] = "<ISO8601>"
        steps.append(step)
    
    return steps
```

### D4 健康检查（Health Check）

```python
def run_health_checks(snapshot, config):
    """运行健康检查"""
    
    checks = []
    
    # 检查 1: 服务可用性
    check = check_service_availability(config)
    checks.append({
        "id": "service_availability",
        "description": "服务可用性",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 2: 性能指标
    check = check_performance_metrics(config)
    checks.append({
        "id": "performance_metrics",
        "description": "性能指标",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 3: 错误日志
    check = check_error_logs(config)
    checks.append({
        "id": "error_logs",
        "description": "错误日志",
        "status": check["status"],
        "details": check["details"]
    })
    
    all_passed = all(c["status"] == "pass" for c in checks)
    
    return {
        "status": "passed" if all_passed else "failed",
        "checks": checks
    }
```

### D5 部署回滚（Deployment Rollback）

```python
def rollback_deployment(snapshot, config, reason):
    """回滚部署"""
    
    rollback = {
        "status": "triggered",
        "triggered_at": "<ISO8601>",
        "trigger_reason": reason,
        "steps": []
    }
    
    # 执行回滚
    for step in reversed(snapshot.deployment.steps):
        rollback_step = {
            "id": step["id"],
            "type": "rollback",
            "status": "pending"
        }
        
        result = rollback_instance(step["instance"], config)
        
        if result.success:
            rollback_step["status"] = "completed"
        else:
            rollback_step["status"] = "failed"
            rollback_step["error"] = result.error
        
        rollback["steps"].append(rollback_step)
    
    rollback["completed_at"] = "<ISO8601>"
    rollback["status"] = "completed" if all(s["status"] == "completed" for s in rollback["steps"]) else "partial"
    
    return rollback
```

### D6 部署报告（Deployment Report）

```python
def generate_deployment_report(deployment, pre_checks, health_checks):
    """生成部署报告"""
    
    report = {
        "status": deployment["status"],
        "started_at": deployment["started_at"],
        "completed_at": deployment["completed_at"],
        "duration": calculate_duration(deployment["started_at"], deployment["completed_at"]),
        "strategy": deployment["strategy"],
        "environment": deployment["environment"],
        "steps": deployment["steps"],
        "pre_checks": pre_checks,
        "health_checks": health_checks,
        "summary": {
            "steps_completed": sum(1 for s in deployment["steps"] if s["status"] == "completed"),
            "steps_failed": sum(1 for s in deployment["steps"] if s["status"] == "failed"),
            "pre_checks_passed": sum(1 for c in pre_checks["checks"] if c["status"] == "pass"),
            "pre_checks_failed": sum(1 for c in pre_checks["checks"] if c["status"] == "fail"),
            "health_checks_passed": sum(1 for c in health_checks["checks"] if c["status"] == "pass"),
            "health_checks_failed": sum(1 for c in health_checks["checks"] if c["status"] == "fail")
        }
    }
    
    return report
```

## 输出契约
- `snapshot.deployment`（`status` / `strategy` / `environment` / `steps` / `pre_checks` / `health_checks` / `summary`）
- 部署报告文件，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 前置检查失败 → 标记 `status: failed`，拒绝部署
- 部署失败 → 标记 `status: failed`，触发回滚
- 健康检查失败 → 标记 `health_checks.status: failed`，建议回滚

## 何时升级
- 部署失败 → `pax-rollback`
- 健康检查失败 → `pax-council`
- 需要用户确认 → 返回上游阶段