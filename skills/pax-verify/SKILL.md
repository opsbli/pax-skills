---
name: pax-verify
description: >
    Use when: 运行中验证，有界循环 + 五态印章。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 1.0.0
family: pax
layer: L4
optional: true
requires_snapshot: true
---

# pax-verify


## Overview

运行中验证 Skill。在长任务执行过程中周期性检查契约与前置条件。

## When to Use

长耗时任务执行中，编排层或运行监控触发验证。

## Common Pitfalls

- 验证频率过高影响执行效率。
- 只检查静态契约，忽略运行时状态。
- 发现问题后未告警。

## Verification Checklist

- [ ] 验证频率与任务时长匹配
- [ ] 验证覆盖静态契约和运行时状态
- [ ] 异常已触发告警并写入快照
## Execution Contract
- 前置门禁：可被任意 L0/L1/L2 调用；被验证对象与成功标准可读取
- 未通过门禁：返回 `blocked`
- 版本检查：`pax-ops/versions.json`
- 独立：验证不依赖被验证对象的自证
- 可审计：每次印章必须可追溯到具体证据
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：运行中验证，有界循环 + 五态印章
- 不做什么：不认领路由落点、不改变主流程、不修改快照字段

## 输入
- 必需：被验证对象（执行结果 / 变更 diff / 输出）与成功标准
- 可选：超时预算、重试次数

## 工作流

### V1 验证对象识别（Subject Identification）

```python
def identify_subject(input):
    """识别被验证对象"""
    
    subject = {
        "type": "execution" | "diff" | "output" | "data" | "configuration",
        "content": input.content,
        "metadata": input.metadata
    }
    
    return subject
```

### V2 验证标准解析（Criteria Parsing）

```python
def parse_criteria(criteria):
    """解析成功标准"""
    
    criteria_list = []
    
    for item in criteria:
        criterion = {
            "id": f"C{len(criteria_list) + 1}",
            "description": item.description,
            "method": item.method,  # automated | manual
            "automatable": item.method == "automated",
            "weight": item.weight,  # high | medium | low
            "threshold": item.threshold
        }
        criteria_list.append(criterion)
    
    return criteria_list
```

### V3 有界循环验证（Bounded Loop Verification）

**循环参数**：
- 默认上限：3 次
- 超时预算：默认 5 分钟
- 重试间隔：指数退避（1s, 2s, 4s）

```python
def bounded_loop_verify(subject, criteria, max_attempts=3):
    """有界循环验证"""
    
    results = []
    attempts = 0
    
    for attempt in range(max_attempts):
        attempts = attempt + 1
        
        # 执行验证
        attempt_result = execute_verification(subject, criteria)
        results.append(attempt_result)
        
        # 检查是否通过
        if attempt_result.all_pass:
            return build_stamp("verified", results, attempt_result)
        
        # 检查是否可重试
        if not attempt_result.retriable:
            return build_stamp("needs_fix", results, attempt_result)
        
        # 检查超时
        if attempt_result.duration > timeout_budget:
            return build_stamp("partial", results, attempt_result)
        
        # 重试间隔
        wait(attempt_result.retry_delay)
    
    # 超过上限
    return build_stamp("partial", results, results[-1])
```

### V4 验证方法（Verification Methods）

| 方法 | 适用对象 | 工具 | 自动化 |
|------|----------|------|--------|
| `test_execution` | 代码变更 | pytest, jest, etc. | ✅ |
| `diff_analysis` | 代码 diff | git diff, regex | ✅ |
| `data_query` | 数据变更 | SQL, mongosh | ✅ |
| `config_check` | 配置变更 | 配置文件解析 | ✅ |
| `manual_review` | 代码审查 | 人工检查 | ❌ |
| `performance_test` | 性能验证 | 压测工具 | ✅ |

### V4.1 断言有效性检查（Assertion Validity Check）

对 `test_execution` 类验证对象，除"测试是否通过"外，还需检查断言的**观察深度**——只检查 HTTP 200 或 `success: true` 的断言视为无效，不产生 `verified` 印章。

| 断言深度 | 示例 | 印章允许值 |
|---|---|---|
| D0 调用型 | 仅调用函数，无断言 | 仅 `partial`，`confidence: low` |
| D1 结果型 | 仅断言返回值 / HTTP status | `partial`，`confidence: low` |
| D2 业务字段型 | 断言关键业务字段（金额、状态、计数） | `verified` 或 `partial` |
| D3 副作用型 | 断言 DB 写入 / 缓存 / 日志 / 消息 / 下游接口 | `verified` |

**规则**：
- 单条验证若最高只到 D1，印章上限为 `partial`；
- 全部验证均为 D0/D1 时，禁止给出 `verified`；
- 印章结构里追加 `assertion_depth` 字段，记录本次验证达到的最高断言深度。

> 本检查关心“证据本身能否被采信”；测试有效性的 PIE 三问关心“测试能否发现缺陷”，两者互补而非重复。

### V5 证据收集（Evidence Collection）

每条验证结果必须收集证据：

```yaml
evidence:
  - criterion_id: C1
    description: "所有单元测试通过"
    method: test_execution
    result: pass
    data: "15/15 tests passed"
    timestamp: "<ISO8601>"
    source: "pytest output"
    confidence: high
  - criterion_id: C2
    description: "变更在授权范围内"
    method: diff_analysis
    result: pass
    data: "3 files modified, all within authorized scope"
    timestamp: "<ISO8601>"
    source: "git diff + contract"
    confidence: high
```

### V6 五态印章（Five-State Stamp）

| 印章 | 语义 | 条件 |
|------|------|------|
| `verified` | 全部标准通过 | 所有 criteria 通过 |
| `needs_fix` | 存在未通过项 | 至少一个 high 权重 criteria 失败 |
| `partial` | 部分通过，允许延期 | medium/low 权重 criteria 失败 |
| `blocked` | 证据不足或依赖不可用 | 无法执行验证 |
| `needs_review` | 超出验证权限 | 需要人工介入 |

**印章结构**（作为一条 seal **追加**到 `snapshot.quality.verification_seals` 数组末位）：
```yaml
seal:  # 追加到 snapshot.quality.verification_seals
  result: verified | needs_fix | partial | blocked | needs_review
  confidence: high | medium | low
  attempts: <验证次数>
  duration: "<总耗时>"
  evidence:
    - criterion_id: C1
      result: verified
      data: "..."
      source: "..."
      confidence: high
    - criterion_id: C2
      result: needs_fix
      data: "..."
      source: "..."
      confidence: medium
  summary: "<验证摘要>"
  timestamp: "<ISO8601>"
  verified_by: "pax-verify"
```

### V7 置信度评估（Confidence Assessment）

```python
def assess_confidence(evidence):
    """评估验证置信度"""
    
    confidences = [e.confidence for e in evidence]
    
    if all(c == "high" for c in confidences):
        return "high"
    elif any(c == "high" for c in confidences):
        return "medium"
    else:
        return "low"
```

**置信度规则**：

| 置信度 | 条件 | 处理 |
|--------|------|------|
| `high` | 所有证据来自自动化验证 | 可直接采信 |
| `medium` | 混合自动化和手动证据 | 建议人工复核 |
| `low` | 仅手动证据或间接证据 | 需要更多验证 |

### V8 失败处理（Failure Handling）

```python
def handle_failure(result):
    """处理验证失败"""
    
    # 条件 1: 验证标准缺失
    if not result.criteria:
        return "blocked", "验证标准缺失"
    
    # 条件 2: 依赖不可用
    if result.dependencies_unavailable:
        return "blocked", f"依赖不可用: {result.dependencies_unavailable}"
    
    # 条件 3: 循环超过上限
    if result.attempts >= result.max_attempts:
        return "partial", f"验证循环超过上限 ({result.max_attempts} 次)"
    
    # 条件 4: 超出验证权限
    if result.requires_manual_review:
        return "needs_review", "需要人工介入"
    
    # 条件 5: 存在失败项
    if result.has_failures:
        high_failures = [f for f in result.failures if f.weight == "high"]
        if high_failures:
            return "needs_fix", f"存在 {len(high_failures)} 个 high 权重失败项"
        else:
            return "partial", "部分通过，允许延期"
    
    return "verified", "全部通过"
```

## 输出契约
- `snapshot.quality.verification_seals`：追加一条五态印章（含证据与置信度），格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 验证标准缺失 → 返回 `blocked`
- 循环超过上限 → 强制收敛并返回 `partial`
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 问题超出验证范围 → 请求人工介入
- 高风险或未决争议 → 升级至主流程或人工审批
