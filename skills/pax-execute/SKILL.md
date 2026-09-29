---
name: pax-execute
description: >
  在契约约束下执行，带审计和回滚。当 `plan.status == frozen` 且契约已确认，需要按计划实施时使用。
version: 0.2.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-execute

## Execution Contract
- 前置门禁：`contract` 已确认，`plan.status == frozen`
- 未通过门禁：拒绝启动，返回上游阶段
- 版本检查：`pax-ops/versions.json`
- 未通过内环验证不得标记完成
- 偏离契约必须暂停并重新协商
- fix 模式必须包含回归测试
- 禁止"顺手改别的"、禁止在根因判断有误时自行重新诊断

## 职责边界
- 做什么：在契约约束下执行，带审计和回滚
- 不做什么：不修改契约、不做独立评审、不做自诊断

## 输入
- 必需：`snapshot.plan`（`status: frozen`）、`snapshot.contract`
- 可选：`snapshot.diagnosis`（fix 模式必需）

## 工作流

### E1 门禁校验（Gate Check）

```python
def check_gate(snapshot):
    """校验前置门禁"""
    
    if not snapshot.contract.authorization.confirmed:
        return False, "契约未确认"
    
    if snapshot.plan.status != "frozen":
        return False, f"计划状态为 {snapshot.plan.status}，需要 frozen"
    
    if snapshot.plan.frozen_at is None:
        return False, "计划未冻结"
    
    return True, "门禁通过"
```

### E2 执行模式选择（Mode Selection）

| 模式 | 触发条件 | 约束 |
|------|----------|------|
| `normal` | `orchestration.intent.primary != diagnose_fix` | 常规执行 |
| `fix` | `orchestration.intent.primary == diagnose_fix` | 必须针对已确认根因，必须包含回归测试 |

**fix 模式额外约束**：
- 修复必须针对已确认根因，不能"顺手改别的"
- 必须包含回归测试
- 必须验证修复不引入新问题
- 修复后重新运行 `pax-diagnose` 的最小复现案例
- 若发现根因判断有误，不允许自行重新诊断，必须返回 `pax-diagnose`

### E3 步骤执行（Step Execution）

```python
def execute_steps(plan):
    """按计划步骤执行"""
    
    log = []
    changes = []
    deviations = []
    
    for step in sorted(plan.steps, key=lambda s: topological_sort(s, plan.dependencies)):
        # 检查依赖
        if not check_dependencies(step, plan):
            return False, f"步骤 {step.id} 依赖未满足"
        
        # 数据订正步骤：检查存储引擎
        if step.prerequisite == "storage_backend_confirmed":
            if not verify_storage_backend(step):
                return False, f"步骤 {step.id} 存储引擎与 plan 不一致"
        
        # 执行步骤
        result = execute_step(step)
        
        # 内环验证
        if not verify_step(step, result):
            # 尝试修复
            fix_result = fix_step(step, result)
            if not fix_result:
                return False, f"步骤 {step.id} 内环验证失败"
            result = fix_result
        
        # 记录日志
        log.append({
            "step": step.id,
            "action": step.action,
            "result": "success",
            "timestamp": "<ISO8601>",
            "duration": "<执行时间>"
        })
        
        # 记录变更
        if result.changes:
            changes.extend(result.changes)
        
        # 检测偏差
        if result.deviations:
            deviations.extend(result.deviations)
            if exceeds_deviation_tolerance(deviations):
                return False, "偏离超出容忍度，暂停并重新协商"
    
    return True, {
        "log": log,
        "changes": changes,
        "deviations": deviations
    }
```

### E4 内环验证（Inner Loop Verification）

**验证循环**：做 → 验 → 修

```python
def verify_step(step, result):
    """验证步骤结果"""
    
    # 方法 1: 单元测试
    if "test" in step.verification.method.lower():
        return run_tests(step.verification.criteria)
    
    # 方法 2: 代码审查
    if "review" in step.verification.method.lower():
        return review_changes(result.changes)
    
    # 方法 3: 数据验证
    if "data" in step.verification.method.lower():
        return verify_data_consistency(step.verification.criteria)
    
    # 方法 4: 集成测试
    if "integration" in step.verification.method.lower():
        return run_integration_tests(step.verification.criteria)
    
    return True  # 默认通过
```

**修复循环**（最多 3 次）：
```python
def fix_step(step, result):
    """修复步骤"""
    
    for attempt in range(3):
        # 分析失败原因
        reason = analyze_failure(step, result)
        
        # 尝试修复
        fix = apply_fix(step, reason)
        
        # 重新验证
        if verify_step(step, fix):
            return True
        
        # 记录修复尝试
        log_fix_attempt(step.id, attempt + 1, reason, fix)
    
    return False  # 3 次修复失败
```

### E5 变更追踪（Change Tracking）

每个变更必须记录：

```yaml
changes:
  - id: C1
    step: S1
    file: "<文件路径>"
    type: add | modify | delete
    summary: "<变更摘要>"
    lines_added: <行数>
    lines_deleted: <行数>
    diff_hash: "<diff 哈希>"
    timestamp: "<ISO8601>"
```

**变更边界检查**：
```python
def check_change_boundary(changes, contract):
    """检查变更是否在契约授权范围内"""
    
    authorized_files = set(contract.authorization.files or [])
    authorized_modules = set(contract.authorization.modules or [])
    
    for change in changes:
        file_in_scope = any(
            change.file.startswith(module) 
            for module in authorized_modules
        ) if authorized_modules else change.file in authorized_files
        
        if not file_in_scope:
            return False, f"变更 {change.file} 超出授权范围"
    
    return True, None
```

### E6 偏差检测（Deviation Detection）

**偏差类型**：

| 类型 | 条件 | 严重度 |
|------|------|--------|
| `scope` | 变更超出授权范围 | high |
| `behavior` | 行为与预期不符 | medium |
| `timeline` | 执行时间超出预算 | low |
| `dependency` | 依赖未满足 | high |

**偏差容忍度**：

| 严重度 | 最大容忍数 | 超出后 |
|--------|------------|--------|
| `high` | 0 | 立即暂停 |
| `medium` | 2 | 暂停并报告 |
| `low` | 5 | 记录并继续 |

```yaml
deviations:
  - id: D1
    step: S1
    type: scope
    severity: high
    description: "<偏差描述>"
    detected_at: "<ISO8601>"
    action: "<处理动作>"
    resolved: true | false
```

### E7 执行日志（Execution Log）

```yaml
execution:
  mode: normal | fix
  log:
    - step: S1
      action: "修复根因代码"
      result: success | failed | skipped
      timestamp: "<ISO8601>"
      duration: "5min"
      details: "<执行详情>"
    - step: S2
      action: "编写回归测试"
      result: success
      timestamp: "<ISO8601>"
      duration: "10min"
      details: "<执行详情>"
  deviations:
    - id: D1
      step: S1
      type: scope
      severity: high
      description: "修改了 contract 未授权的文件"
      action: "已回滚该文件变更"
      resolved: true
  changes:
    - id: C1
      step: S1
      file: "src/service/cmdb/validator.py"
      type: modify
      summary: "修复时间类型字段校验逻辑"
      lines_added: 5
      lines_deleted: 3
  status: completed | failed | paused
  completed_at: "<ISO8601>"
```

### E8 完成验证（Completion Check）

```python
def check_completion(execution, plan):
    """检查执行是否完成"""
    
    # 条件 1: 所有步骤已执行
    if execution.status != "completed":
        return False, f"执行状态为 {execution.status}"
    
    # 条件 2: 无未解决的 high 偏差
    unresolved_high = [
        d for d in execution.deviations 
        if d.severity == "high" and not d.resolved
    ]
    if unresolved_high:
        return False, f"存在 {len(unresolved_high)} 个未解决的 high 偏差"
    
    # 条件 3: fix 模式必须包含回归测试
    if execution.mode == "fix":
        has_regression_test = any(
            "regression" in s.action.lower() or "test" in s.action.lower()
            for s in plan.steps
        )
        if not has_regression_test:
            return False, "fix 模式缺少回归测试"
    
    return True, "执行完成"
```

## 输出契约
- `snapshot.execution`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 契约未确认 → 返回上游阶段
- `plan.status != frozen` → 返回规划阶段
- 内环验证失败 → 回滚并暂停
- 偏离契约 → 暂停，写入 `deviations[]`，重新协商
- 根因判断有误（fix 模式） → 返回诊断阶段

## 何时升级
- 需要独立验证 → `pax-verify`
- 计划无法执行 → 返回规划阶段
- 偏离超出容忍度 → `pax-council`
- 需要独立评审 → `pax-review`
