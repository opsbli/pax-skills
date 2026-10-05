---
name: pax-worker-implement
description: >
    Use when: 有界实现任务执行。由 pax-execute 在步骤复杂度较高时委派调用（step.complexity == "high" 且 step.delegation_target 非空）。L3 层工具适配，接口由上层定义。
version: 1.0.0
family: pax
layer: L3
optional: true
requires_snapshot: true
---

# pax-worker-implement


## Overview

实现型子任务 Skill。有界、单点，只做一个可交付的实现步骤。

## When to Use

上层计划中有一个独立的实现子任务需要落地。

## Common Pitfalls

- 一次做太多子任务，输出失控。
- 破坏原有文件结构。
- 未回滚失败改动。

## Verification Checklist

- [ ] 子任务边界明确且交付可验证
- [ ] 改动文件清单已回收到上层快照
- [ ] 失败路径可回滚
## Execution Contract
- 前置门禁：调用方已定义任务边界与输入
- 未通过门禁：拒绝执行
- 版本检查：`pax-ops/versions.json`
- 沙箱：必须在 isolated FS / network 下运行
- 无头：不得依赖交互输入
- 边界：不得跨越调用方给定的任务范围
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：将有界实现任务委托给固定 worker，产出变更 diff
- 不做什么：不做路由决策、不修改上层快照字段、不扩大任务范围

## 输入
- 必需：任务描述、约束、输入上下文、变更边界
- 可选：优先级、超时、期望测试清单

## 工作流

### W1 任务解析（Task Parsing）

```yaml
task:
  id: "I001"
  description: "修复 CMDB 字段校验逻辑"
  type: bug_fix | feature | refactor | test | documentation
  constraints:
    - "只修改 src/ops/cmdb/validator.py"
    - "不修改其他文件"
    - "必须通过现有测试"
  inputs:
    - type: file_path
      value: "src/ops/cmdb/validator.py"
    - type: diagnosis
      value: "诊断报告 D001"
    - type: test_spec
      value: "测试规格 S001"
  change_boundary:
    allowed_files:
      - "src/ops/cmdb/validator.py"
    forbidden_files:
      - "src/ops/cmdb/**"  # 除 validator.py 外
    max_files: 3
    max_lines_changed: 50
  expected_tests:
    - "test_validator.py::test_time_field_validation"
    - "test_validator.py::test_string_field_validation"
  priority: high | medium | low
  timeout: 300  # seconds
```

### W2 沙箱准备（Sandbox Preparation）

```python
def prepare_sandbox(task):
    """准备沙箱"""
    
    # 条件 1: 文件系统隔离
    fs_isolation = {
        "enabled": True,
        "root": "/sandbox/fs",
        "allowed_paths": task.change_boundary.allowed_files,
        "writable": True  # 与 research 不同，implement 需要写权限
    }
    
    # 条件 2: 网络隔离
    network_isolation = {
        "enabled": True,
        "allowed_domains": [],  # 默认不允许网络访问
        "blocked_domains": ["*"]
    }
    
    # 条件 3: 无头模式
    headless_mode = {
        "enabled": True,
        "no_interactive_input": True,
        "no_ui": True
    }
    
    # 条件 4: Git 沙箱
    git_sandbox = {
        "enabled": True,
        "branch": "feature/task-I001",
        "commit_allowed": True
    }
    
    sandbox = {
        "fs": fs_isolation,
        "network": network_isolation,
        "headless": headless_mode,
        "git": git_sandbox,
        "timeout": task.timeout
    }
    
    return sandbox
```

### W3 实现任务执行（Implementation Execution）

**实现类型**：

| 类型 | 操作 | 输出 |
|------|------|------|
| `bug_fix` | 修复 bug | diff、测试通过 |
| `feature` | 添加功能 | diff、测试通过 |
| `refactor` | 重构代码 | diff、测试通过 |
| `test` | 添加测试 | diff、测试覆盖 |
| `documentation` | 更新文档 | diff、文档完整 |

**执行流程**：
```python
def execute_implementation(task, sandbox):
    """执行实现任务"""
    
    # 条件 1: 检查边界
    if not check_change_boundary(task.change_boundary):
        return {
            "status": "blocked",
            "reason": "变更边界无效",
            "details": "allowed_files 与 forbidden_files 冲突"
        }
    
    # 条件 2: 读取输入
    inputs = read_inputs(task.inputs)
    
    # 条件 3: 执行实现
    result = perform_implementation(task, inputs, sandbox)
    
    # 条件 4: 检查变更边界
    changes = collect_changes()
    if not check_changes_within_boundary(changes, task.change_boundary):
        return {
            "status": "failed",
            "reason": "变更超出边界",
            "details": f"变更了 {len(changes)} 个文件，超出上限 {task.change_boundary.max_files}"
        }
    
    # 条件 5: 运行测试
    test_results = run_tests(task.expected_tests)
    
    # 条件 6: 收集 diff
    diff = collect_diff()
    
    return {
        "status": "success" if test_results.passed else "failed",
        "changes": changes,
        "diff": diff,
        "test_results": test_results,
        "logs": result.logs
    }
```

### W4 变更收集（Change Collection）

```yaml
changes:
  - id: "C1"
    file: "src/ops/cmdb/validator.py"
    type: modify
    lines_added: 5
    lines_deleted: 3
    summary: "修复时间类型字段校验逻辑"
    diff_hash: "abc123"
  
  - id: "C2"
    file: "src/ops/cmdb/test_validator.py"
    type: modify
    lines_added: 10
    lines_deleted: 0
    summary: "添加时间字段测试用例"
    diff_hash: "def456"

diff:
  - file: "src/ops/cmdb/validator.py"
    changes:
      - type: add
        line: 25
        content: "if is_time_field(field_type):"
      - type: add
        line: 26
        content: "    return validate_time_field(value)"
      - type: delete
        line: 30
        content: "return validate_string_field(value)"
  
  - file: "src/ops/cmdb/test_validator.py"
    changes:
      - type: add
        line: 50
        content: "def test_time_field_validation():"
      - type: add
        line: 51
        content: "    assert validate_field(time_field, '2024-01-01') == True"
```

### W5 测试执行（Test Execution）

```yaml
test_results:
  status: passed | failed | skipped
  total: 5
  passed: 5
  failed: 0
  skipped: 0
  duration: 3.5  # seconds
  tests:
    - name: "test_validator.py::test_time_field_validation"
      status: passed
      duration: 0.1
    - name: "test_validator.py::test_string_field_validation"
      status: passed
      duration: 0.1
    - name: "test_validator.py::test_number_field_validation"
      status: passed
      duration: 0.1
    - name: "test_validator.py::test_date_field_validation"
      status: passed
      duration: 0.1
    - name: "test_validator.py::test_null_field_validation"
      status: passed
      duration: 0.1
  coverage:
    total: 100
    covered: 95
    percentage: 95.0
```

### W6 打包返回（Package and Return）

```yaml
worker_response:
  task_id: "I001"
  status: success | failed | partial | blocked
  exit_code: 0
  changes:
    - id: "C1"
      file: "<文件路径>"
      type: add | modify | delete
      lines_added: <行数>
      lines_deleted: <行数>
      summary: "<变更摘要>"
      diff_hash: "<diff 哈希>"
  diff:
    - file: "<文件路径>"
      changes:
        - type: add | delete | modify
          line: <行号>
          content: "<内容>"
  test_results:
    status: passed | failed | skipped
    total: <数量>
    passed: <数量>
    failed: <数量>
    skipped: <数量>
    duration: <时间>
    tests:
      - name: "<测试名称>"
        status: passed | failed | skipped
        duration: <时间>
  logs:
    - timestamp: "<ISO8601>"
      level: info | warn | error
      message: "<日志消息>"
  metadata:
    duration: "<执行时间>"
    files_changed: <数量>
    lines_changed: <数量>
    tests_run: <数量>
    tests_passed: <数量>
  confidence: high | medium | low
  timestamp: "<ISO8601>"
  worker: "pax-worker-implement"
```

### W7 失败处理（Failure Handling）

```python
def handle_failure(task, result):
    """处理失败"""
    
    # 条件 1: 任务超时
    if result.exit_code == 2:
        return {
            "status": "partial",
            "reason": "任务超时",
            "changes": result.changes,  # 返回部分变更
            "recommendation": "增加超时时间或缩小任务范围"
        }
    
    # 条件 2: 沙箱失败
    if result.exit_code == 3 and result.error == "sandbox_failed":
        return {
            "status": "blocked",
            "reason": "沙箱失败",
            "recommendation": "检查沙箱配置"
        }
    
    # 条件 3: 变更超出边界
    if result.exit_code == 1 and result.error == "boundary_exceeded":
        return {
            "status": "failed",
            "reason": "变更超出边界",
            "details": f"变更了 {len(result.changes)} 个文件，超出上限",
            "recommendation": "缩小任务范围或增加边界上限"
        }
    
    # 条件 4: 测试失败
    if result.exit_code == 1 and result.error == "tests_failed":
        return {
            "status": "failed",
            "reason": "测试失败",
            "failed_tests": result.test_results.failed_tests,
            "recommendation": "修复实现或调整测试"
        }
    
    # 条件 5: 任务超出能力
    if result.exit_code == 1 and result.error == "task_too_complex":
        return {
            "status": "blocked",
            "reason": "任务超出 worker 能力",
            "recommendation": "拆分任务或请求人工协助"
        }
    
    return None  # 正常执行
```

## 输出契约
- 变更 diff、执行日志、退出码、测试结果

## 失败模式
- 任务超时 → kill 并返回 `partial`
- 沙箱失败 → 拒绝执行
- 变更超出给定边界 → 拒绝返回，附说明
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 任务超出 worker 能力 → 返回上游阶段请求重规划
