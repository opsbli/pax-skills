---
name: pax-rollback
description: >
  自动化回滚。此 skill 由 pax-orchestrate 在编排路由中调用，用于在任务执行失败或出现严重问题时自动回滚到安全状态。
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-rollback

## Execution Contract
- 前置门禁：`snapshot.plan.status == frozen` 且 `snapshot.plan.rollback_strategy` 存在
- 未通过门禁：拒绝启动，返回规划阶段
- 版本检查：`pax-ops/versions.json`
- 禁止在回滚过程中修改快照
- 禁止在未确认回滚方案时执行回滚

## 职责边界
- 做什么：执行回滚方案、验证回滚结果、记录回滚日志
- 不做什么：不修复问题、不做诊断、不规划新方案

## 输入
- 必需：`snapshot.plan`、`snapshot.execution`
- 可选：回滚配置、回滚策略

## 工作流

### R1 回滚触发（Rollback Trigger）

```python
def trigger_rollback(snapshot, trigger_reason):
    """触发回滚"""
    
    rollback = {
        "status": "triggered",
        "triggered_at": "<ISO8601>",
        "trigger_reason": trigger_reason,
        "trigger_source": "user" | "monitor" | "system",
        "plan_id": snapshot.plan.id,
        "execution_id": snapshot.execution.id
    }
    
    return rollback
```

### R2 回滚方案选择（Rollback Plan Selection）

```python
def select_rollback_plan(snapshot, trigger_reason):
    """选择回滚方案"""
    
    plan = snapshot.plan
    rollback_strategy = plan.rollback_strategy
    
    # 根据触发原因选择回滚策略
    if trigger_reason == "task_failure":
        strategy = rollback_strategy.get("on_failure", "git_revert")
    elif trigger_reason == "monitor_alert":
        strategy = rollback_strategy.get("on_alert", "stop_execution")
    elif trigger_reason == "user_request":
        strategy = rollback_strategy.get("on_request", "full_revert")
    else:
        strategy = rollback_strategy.get("default", "git_revert")
    
    return strategy
```

### R3 回滚执行（Rollback Execution）

```python
def execute_rollback(rollback, strategy, snapshot):
    """执行回滚"""
    
    rollback["status"] = "executing"
    rollback["started_at"] = "<ISO8601>"
    
    steps = []
    
    # 根据策略执行回滚
    if strategy == "git_revert":
        steps.append(execute_git_revert(snapshot))
    elif strategy == "delete_file":
        steps.append(execute_delete_file(snapshot))
    elif strategy == "config_revert":
        steps.append(execute_config_revert(snapshot))
    elif strategy == "data_rollback":
        steps.append(execute_data_rollback(snapshot))
    elif strategy == "stop_execution":
        steps.append(execute_stop_execution(snapshot))
    elif strategy == "full_revert":
        steps.append(execute_git_revert(snapshot))
        steps.append(execute_delete_file(snapshot))
    
    rollback["steps"] = steps
    rollback["completed_at"] = "<ISO8601>"
    
    return rollback
```

**Git 回滚**：
```python
def execute_git_revert(snapshot):
    """执行 Git 回滚"""
    
    commits = snapshot.execution.commits
    rollback_steps = []
    
    for commit in reversed(commits):
        step = {
            "type": "git_revert",
            "commit": commit["hash"],
            "message": commit["message"],
            "status": "pending"
        }
        
        # 执行 git revert
        result = run_command(f"git revert {commit['hash']}")
        
        if result.success:
            step["status"] = "completed"
        else:
            step["status"] = "failed"
            step["error"] = result.error
        
        rollback_steps.append(step)
    
    return {
        "strategy": "git_revert",
        "steps": rollback_steps,
        "status": "completed" if all(s["status"] == "completed" for s in rollback_steps) else "partial"
    }
```

**数据回滚**：
```python
def execute_data_rollback(snapshot):
    """执行数据回滚"""
    
    steps = []
    
    # 查找数据订正步骤
    data_steps = [s for s in snapshot.plan.steps if s.get("prerequisite") == "storage_backend_confirmed"]
    
    for step in data_steps:
        rollback_script = step.get("rollback_script")
        if rollback_script:
            result = run_command(rollback_script)
            steps.append({
                "type": "data_rollback",
                "script": rollback_script,
                "status": "completed" if result.success else "failed"
            })
    
    return {
        "strategy": "data_rollback",
        "steps": steps,
        "status": "completed" if all(s["status"] == "completed" for s in steps) else "partial"
    }
```

### R4 回滚验证（Rollback Verification）

```python
def verify_rollback(rollback, snapshot):
    """验证回滚结果"""
    
    verification = {
        "status": "pending",
        "checks": []
    }
    
    # 检查 1: 代码已回滚
    check = verify_git_revert(snapshot)
    verification["checks"].append({
        "type": "code_rollback",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 2: 数据已回滚
    check = verify_data_rollback(snapshot)
    verification["checks"].append({
        "type": "data_rollback",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 检查 3: 服务状态
    check = verify_service_status(snapshot)
    verification["checks"].append({
        "type": "service_status",
        "status": check["status"],
        "details": check["details"]
    })
    
    # 汇总结果
    all_passed = all(c["status"] == "pass" for c in verification["checks"])
    verification["status"] = "passed" if all_passed else "failed"
    
    return verification
```

### R5 回滚报告（Rollback Report）

```python
def generate_rollback_report(rollback, verification):
    """生成回滚报告"""
    
    report = {
        "rollback_id": rollback["id"],
        "trigger_reason": rollback["trigger_reason"],
        "trigger_time": rollback["triggered_at"],
        "strategy": rollback["strategy"],
        "execution_time": rollback["completed_at"],
        "steps": rollback["steps"],
        "verification": verification,
        "summary": {
            "status": verification["status"],
            "steps_completed": sum(1 for s in rollback["steps"] if s["status"] == "completed"),
            "steps_failed": sum(1 for s in rollback["steps"] if s["status"] == "failed"),
            "checks_passed": sum(1 for c in verification["checks"] if c["status"] == "pass"),
            "checks_failed": sum(1 for c in verification["checks"] if c["status"] == "fail")
        }
    }
    
    return report
```

## 输出契约
- `snapshot.rollback`（`status` / `trigger_reason` / `strategy` / `steps` / `verification` / `summary`）
- 回滚报告文件，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 回滚失败 → 标记 `status: failed`，记录错误信息，通知用户
- 验证失败 → 标记 `verification.status: failed`，记录失败原因
- 回滚超时 → 标记 `timeout: true`，部分回滚，记录已回滚步骤

## 何时升级
- 回滚失败 → `pax-council`
- 需要用户确认 → `pax-orchestrate`
- 需要手动回滚 → `pax-execute`