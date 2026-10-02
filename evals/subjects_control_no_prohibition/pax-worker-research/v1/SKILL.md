---
name: pax-worker-research
description: >
    Use when: 有界研究任务执行。L3 层工具适配，接口由上层定义。
version: 0.2.0
family: pax
layer: L3
optional: true
requires_snapshot: true
---

# pax-worker-research


## Overview

研究型子任务 Skill。有界、单点，只做调研产出结论。

## When to Use

上层需要一项调研结果（例如查一个库、验证一个说法）时。

## Common Pitfalls

- 任务边界外扩，越权做决策。
- 未记录证据来源。
- 未回收到上层快照。

## Verification Checklist

- [ ] 调研范围明确且未越界
- [ ] 结论附有证据链
- [ ] 结果已回收到上层快照
## Execution Contract
- 前置门禁：调用方已定义任务边界与输入
- 未通过门禁：拒绝执行
- 版本检查：`pax-ops/versions.json`
- 沙箱：必须在 isolated FS / network 下运行
- 无头：不得依赖交互输入
- 只读：不修改调用方快照字段
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：将有界研究/检索任务委托给固定 worker
- 不做什么：不做路由决策、不修改上层快照字段、不做写操作

## 输入
- 必需：任务描述、约束、输入上下文
- 可选：优先级、超时、检索源白名单

## 工作流

### W1 任务解析（Task Parsing）

```yaml
task:
  id: "R001"
  description: "检索 CMDB 模块的存储后端配置"
  type: code_search | documentation | dependency | configuration | runtime_probe
  constraints:
    - "只读操作"
    - "不执行写操作"
    - "不修改任何文件"
  inputs:
    - type: file_path
      value: "src/ops/cmdb/"
    - type: search_query
      value: "MongoDB|mysql|postgresql"
  outputs_expected:
    - type: structured_result
      schema: "storage_backend_info"
  priority: high | medium | low
  timeout: 60  # seconds
  search_sources:
    - type: file_system
      paths: ["src/", "config/", "scripts/"]
    - type: web_search
      allowed_domains: ["docs.mongodb.com", "developer.mozilla.org"]
```

### W2 沙箱准备（Sandbox Preparation）

```python
def prepare_sandbox(task):
    """准备沙箱"""
    
    # 条件 1: 文件系统隔离
    fs_isolation = {
        "enabled": True,
        "root": "/sandbox/fs",
        "allowed_paths": task.constraints.allowed_paths,
        "readonly": True
    }
    
    # 条件 2: 网络隔离
    network_isolation = {
        "enabled": True,
        "allowed_domains": task.search_sources.get("web_search", {}).get("allowed_domains", []),
        "blocked_domains": ["*", "!allowed_domains"]
    }
    
    # 条件 3: 无头模式
    headless_mode = {
        "enabled": True,
        "no_interactive_input": True,
        "no_ui": True
    }
    
    sandbox = {
        "fs": fs_isolation,
        "network": network_isolation,
        "headless": headless_mode,
        "timeout": task.timeout
    }
    
    return sandbox
```

### W3 研究任务执行（Research Execution）

**研究类型**：

| 类型 | 工具 | 输出 |
|------|------|------|
| `code_search` | grep, ripgrep, AST 分析 | 代码匹配、文件路径 |
| `documentation` | 文档解析、网页抓取 | 文档摘要、引用 |
| `dependency` | lock 文件解析、版本对比 | 依赖版本、变更 |
| `configuration` | 配置文件解析 | 配置项、值 |
| `runtime_probe` | 命令执行、API 调用 | 运行时状态、指标 |

**执行流程**：
```python
def execute_research(task, sandbox):
    """执行研究任务"""
    
    results = []
    logs = []
    
    for source in task.search_sources:
        if source.type == "file_system":
            result = search_file_system(source, task)
        elif source.type == "web_search":
            result = search_web(source, task)
        elif source.type == "api":
            result = call_api(source, task)
        else:
            result = {"status": "unsupported", "source": source}
        
        if result.status == "success":
            results.extend(result.data)
            logs.append({
                "source": source,
                "status": "success",
                "count": len(result.data)
            })
        else:
            logs.append({
                "source": source,
                "status": result.status,
                "error": result.error
            })
        
        # 检查超时
        if check_timeout(task.timeout):
            return {
                "status": "partial",
                "results": results,
                "logs": logs,
                "error": "任务超时"
            }
    
    return {
        "status": "success",
        "results": results,
        "logs": logs
    }
```

### W4 输出收集（Output Collection）

```yaml
output:
  status: success | partial | failed | blocked
  exit_code: 0  # 0=success, 1=failed, 2=timeout, 3=blocked
  results:
    - id: "R1"
      source: "src/ops/cmdb/MongoRepository.java"
      type: code_match
      content: "import com.mongodb..."
      relevance: high
      confidence: high
    - id: "R2"
      source: "config/application.yml"
      type: configuration
      content: "spring.data.mongodb.uri: mongodb://..."
      relevance: high
      confidence: high
  logs:
    - timestamp: "<ISO8601>"
      level: info | warn | error
      message: "<日志消息>"
  citations:
    - source: "MongoDB 官方文档"
      url: "https://docs.mongodb.com/..."
      relevance: high
  metadata:
    duration: 45  # seconds
    sources_searched: 5
    results_count: 12
    error_count: 0
```

### W5 打包返回（Package and Return）

```yaml
worker_response:
  task_id: "R001"
  status: success | partial | failed | blocked
  exit_code: 0
  results:
    - id: "R1"
      source: "<来源>"
      type: "<类型>"
      content: "<内容>"
      relevance: high | medium | low
      confidence: high | medium | low
  citations:
    - source: "<引用来源>"
      url: "<URL>"
      relevance: high | medium | low
  logs:
    - timestamp: "<ISO8601>"
      level: info | warn | error
      message: "<消息>"
  metadata:
    duration: "<执行时间>"
    sources_searched: <数量>
    results_count: <数量>
    error_count: <数量>
  confidence: high | medium | low
  timestamp: "<ISO8601>"
  worker: "pax-worker-research"
```

### W6 失败处理（Failure Handling）

```python
def handle_failure(task, result):
    """处理失败"""
    
    # 条件 1: 任务超时
    if result.exit_code == 2:
        return {
            "status": "partial",
            "reason": "任务超时",
            "results": result.results,  # 返回部分结果
            "recommendation": "增加超时时间或缩小搜索范围"
        }
    
    # 条件 2: 沙箱失败
    if result.exit_code == 3 and result.error == "sandbox_failed":
        return {
            "status": "blocked",
            "reason": "沙箱失败",
            "recommendation": "检查沙箱配置"
        }
    
    # 条件 3: 检索源不可用
    if result.exit_code == 1 and result.error == "source_unavailable":
        return {
            "status": "blocked",
            "reason": "检索源不可用",
            "missing_information": [result.source],
            "recommendation": "使用替代检索源"
        }
    
    # 条件 4: 结果不确定
    if result.confidence == "low":
        return {
            "status": "partial",
            "reason": "结果不确定度高",
            "results": result.results,
            "recommendation": "补充上下文或人工验证"
        }
    
    return None  # 正常执行
```

## 输出契约
- 结构化结果、引用来源、执行日志、退出码

## 失败模式
- 任务超时 → kill 并返回 `partial`
- 沙箱失败 → 拒绝执行
- 检索源不可用 → 返回 `blocked`，附 `missing_information`
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 任务超出 worker 能力 → 返回上游阶段请求重规划
- 结果不确定度高 → 请求调用方补充上下文
