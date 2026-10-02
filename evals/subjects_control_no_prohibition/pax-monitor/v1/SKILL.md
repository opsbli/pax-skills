---
name: pax-monitor
description: >
    Use when: 运行中监控和告警。用于监控任务执行过程中的异常情况并触发告警。
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-monitor


## Overview

运行中监控与告警 Skill。持续观察执行状态、指标、错误，触发告警与升级。

## When to Use

长耗时执行、部署、数据订正等需要持续观察的任务。

## Common Pitfalls

- 告警阈值过宽，问题被淹没。
- 只监控不升级，异常无人响应。
- 与运行中验证职责混淆。

## Verification Checklist

- [ ] 监控指标与告警阈值明确
- [ ] 告警触发有升级路径
- [ ] 监控事件已留痕到快照
## Execution Contract
- 前置门禁：`snapshot.plan.status == frozen`
- 未通过门禁：拒绝启动，返回规划阶段
- 版本检查：`pax-ops/versions.json`
- skip_reason：当风险等级为 low 且任务类型为 doc_consult 时可跳过
- 禁止在任务执行完成后继续监控
- 禁止在高风险任务中跳过监控

## 职责边界
- 做什么：监控任务执行过程中的异常情况、触发告警、记录监控日志
- 不做什么：不修复问题、不执行回滚、不做诊断

## 输入
- 必需：`snapshot.plan`、`snapshot.execution`
- 可选：监控配置、告警阈值

## 工作流

### M1 监控初始化（Monitoring Initialization）

```python
def init_monitoring(snapshot, config):
    """初始化监控"""
    
    monitoring = {
        "status": "active",
        "started_at": "<ISO8601>",
        "config": {
            "interval": config.get("interval", "30s"),
            "metrics": config.get("metrics", ["cpu", "memory", "latency"]),
            "alerts": config.get("alerts", [])
        },
        "thresholds": {
            "cpu": config.get("cpu_threshold", 80),
            "memory": config.get("memory_threshold", 80),
            "latency": config.get("latency_threshold", 1000)  # ms
        },
        "alerts_triggered": [],
        "logs": []
    }
    
    return monitoring
```

### M2 指标采集（Metrics Collection）

```python
def collect_metrics(monitoring, execution_context):
    """采集指标"""
    
    metrics = {
        "timestamp": "<ISO8601>",
        "cpu": execution_context.get("cpu", 0),
        "memory": execution_context.get("memory", 0),
        "latency": execution_context.get("latency", 0),
        "error_rate": execution_context.get("error_rate", 0),
        "progress": execution_context.get("progress", 0)
    }
    
    return metrics
```

### M3 异常检测（Anomaly Detection）

```python
def detect_anomalies(metrics, thresholds):
    """检测异常"""
    
    anomalies = []
    
    if metrics["cpu"] > thresholds["cpu"]:
        anomalies.append({
            "type": "high_cpu",
            "value": metrics["cpu"],
            "threshold": thresholds["cpu"],
            "severity": "warning" if metrics["cpu"] < thresholds["cpu"] * 1.2 else "critical"
        })
    
    if metrics["memory"] > thresholds["memory"]:
        anomalies.append({
            "type": "high_memory",
            "value": metrics["memory"],
            "threshold": thresholds["memory"],
            "severity": "warning" if metrics["memory"] < thresholds["memory"] * 1.2 else "critical"
        })
    
    if metrics["latency"] > thresholds["latency"]:
        anomalies.append({
            "type": "high_latency",
            "value": metrics["latency"],
            "threshold": thresholds["latency"],
            "severity": "warning" if metrics["latency"] < thresholds["latency"] * 1.5 else "critical"
        })
    
    return anomalies
```

### M4 告警触发（Alert Triggering）

```python
def trigger_alerts(anomalies, config):
    """触发告警"""
    
    alerts = []
    
    for anomaly in anomalies:
        alert = {
            "id": "<UUID>",
            "type": anomaly["type"],
            "severity": anomaly["severity"],
            "message": f"{anomaly['type']}: {anomaly['value']} (threshold: {anomaly['threshold']})",
            "timestamp": "<ISO8601>",
            "action": "none"
        }
        
        # 根据严重程度决定动作
        if anomaly["severity"] == "critical":
            alert["action"] = "stop_execution"
        elif anomaly["severity"] == "warning":
            alert["action"] = "log_only"
        
        alerts.append(alert)
    
    return alerts
```

### M5 监控日志记录（Monitoring Log Recording）

```python
def log_monitoring_event(monitoring, event):
    """记录监控日志"""
    
    log_entry = {
        "timestamp": "<ISO8601>",
        "event_type": event["type"],
        "event_data": event,
        "status": monitoring["status"]
    }
    
    monitoring["logs"].append(log_entry)
    
    return monitoring
```

### M6 监控结束（Monitoring Termination）

```python
def terminate_monitoring(monitoring):
    """结束监控"""
    
    monitoring["status"] = "completed"
    monitoring["completed_at"] = "<ISO8601>"
    
    # 统计告警
    monitoring["summary"] = {
        "total_alerts": len(monitoring["alerts_triggered"]),
        "critical_alerts": sum(1 for a in monitoring["alerts_triggered"] if a["severity"] == "critical"),
        "warning_alerts": sum(1 for a in monitoring["alerts_triggered"] if a["severity"] == "warning")
    }
    
    return monitoring
```

## 输出契约
- `snapshot.monitoring`（`status` / `config` / `thresholds` / `alerts_triggered` / `logs` / `summary`）
- 监控日志文件，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 指标采集失败 → 降级为日志监控，标注 `degraded: true`
- 告警触发失败 → 记录日志，继续监控
- 监控超时 → 自动结束，标注 `timeout: true`

## 何时升级
- 检测到严重异常 → `pax-council`
- 需要停止执行 → `pax-execute`
- 需要回滚 → `pax-rollback`