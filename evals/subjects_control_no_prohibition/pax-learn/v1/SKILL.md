---
name: pax-learn
description: >
    Use when: 经验沉淀和知识图谱。用于从任务执行中沉淀经验并构建知识图谱。
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-learn


## Overview

经验沉淀与知识图谱 Skill。从执行留痕中提取经验，构建可复用的知识图谱。

## When to Use

大量执行留痕积累后、或自进化触发经验提取时。

## Common Pitfalls

- 经验提取过于主观，缺乏证据。
- 图谱条目重复。
- 未与文档沉淀对齐。

## Verification Checklist

- [ ] 经验提取有证据支撑
- [ ] 知识图谱条目去重
- [ ] 沉淀结果与文档沉淀索引一致
## Execution Contract
- 前置门禁：`snapshot.review.status == completed`
- 未通过门禁：拒绝启动，返回评审阶段
- 版本检查：`pax-ops/versions.json`
- skip_reason：当风险等级为 low 且任务类型为 doc_consult 时可跳过
- 禁止在任务未完成时沉淀经验
- 禁止在经验沉淀过程中修改快照

## 职责边界
- 做什么：沉淀任务经验、构建知识图谱、生成学习报告
- 不做什么：不修改代码、不做诊断、不规划任务

## 输入
- 必需：`snapshot`（完整快照）
- 可选：学习配置、知识图谱配置

## 工作流

### L1 经验提取（Experience Extraction）

```python
def extract_experiences(snapshot):
    """提取任务经验"""
    
    experiences = {
        "status": "extracting",
        "started_at": "<ISO8601>",
        "task_type": snapshot.orchestration.intent.primary,
        "experiences": []
    }
    
    # 从共识提取经验
    if snapshot.consensus:
        experiences["experiences"].append({
            "category": "consensus",
            "title": "需求澄清经验",
            "content": extract_consensus_experience(snapshot.consensus)
        })
    
    # 从诊断提取经验
    if snapshot.diagnosis:
        experiences["experiences"].append({
            "category": "diagnosis",
            "title": "问题诊断经验",
            "content": extract_diagnosis_experience(snapshot.diagnosis)
        })
    
    # 从计划提取经验
    if snapshot.plan:
        experiences["experiences"].append({
            "category": "plan",
            "title": "任务规划经验",
            "content": extract_plan_experience(snapshot.plan)
        })
    
    # 从执行提取经验
    if snapshot.execution:
        experiences["experiences"].append({
            "category": "execution",
            "title": "任务执行经验",
            "content": extract_execution_experience(snapshot.execution)
        })
    
    # 从评审提取经验
    if snapshot.review:
        experiences["experiences"].append({
            "category": "review",
            "title": "结果评审经验",
            "content": extract_review_experience(snapshot.review)
        })
    
    experiences["completed_at"] = "<ISO8601>"
    experiences["status"] = "completed"
    
    return experiences
```

**提取共识经验**：
```python
def extract_consensus_experience(consensus):
    """提取共识经验"""
    
    experience = {
        "key_insights": [],
        "lessons_learned": [],
        "best_practices": []
    }
    
    # 关键洞察
    if consensus.dimensions.goal != "unknown":
        experience["key_insights"].append({
            "type": "goal_clarity",
            "content": "目标清晰度高，快速收敛"
        })
    
    # 经验教训
    if consensus.gaps_remaining:
        experience["lessons_learned"].append({
            "type": "gap_resolution",
            "content": f"发现 {len(consensus.gaps_remaining)} 个缺口，需要加强需求澄清"
        })
    
    # 最佳实践
    experience["best_practices"].append({
        "type": "design_tree",
        "content": "使用设计树引导需求澄清"
    })
    
    return experience
```

### L2 知识图谱构建（Knowledge Graph Construction）

```python
def build_knowledge_graph(snapshot, experiences):
    """构建知识图谱"""
    
    graph = {
        "status": "constructing",
        "started_at": "<ISO8601>",
        "nodes": [],
        "edges": [],
        "relations": []
    }
    
    # 添加节点
    graph["nodes"].extend(add_task_node(snapshot))
    graph["nodes"].extend(add_experience_nodes(experiences))
    
    # 添加边
    graph["edges"].extend(add_edge_nodes(snapshot))
    
    # 添加关系
    graph["relations"].extend(add_relations(snapshot, experiences))
    
    graph["completed_at"] = "<ISO8601>"
    graph["status"] = "completed"
    
    return graph
```

**添加任务节点**：
```python
def add_task_node(snapshot):
    """添加任务节点"""
    
    nodes = [
        {
            "id": "task",
            "type": "task",
            "properties": {
                "intent": snapshot.orchestration.intent.primary,
                "risk": snapshot.orchestration.risk.level,
                "diagnose_required": snapshot.orchestration.diagnose_required,
                "route": snapshot.orchestration.route
            }
        },
        {
            "id": "goal",
            "type": "goal",
            "properties": {
                "statement": snapshot.goal.statement
            }
        }
    ]
    
    return nodes
```

**添加经验节点**：
```python
def add_experience_nodes(experiences):
    """添加经验节点"""
    
    nodes = []
    
    for experience in experiences["experiences"]:
        nodes.append({
            "id": f"experience_{experience['category']}",
            "type": "experience",
            "properties": {
                "category": experience["category"],
                "title": experience["title"]
            }
        })
    
    return nodes
```

**添加边**：
```python
def add_edge_nodes(snapshot):
    """添加边"""
    
    edges = [
        {
            "source": "task",
            "target": "goal",
            "relation": "has_goal"
        }
    ]
    
    # 根据路由添加边
    if snapshot.orchestration.route:
        for i in range(len(snapshot.orchestration.route) - 1):
            edges.append({
                "source": f"stage_{snapshot.orchestration.route[i]}",
                "target": f"stage_{snapshot.orchestration.route[i+1]}",
                "relation": "next"
            })
    
    return edges
```

**添加关系**：
```python
def add_relations(snapshot, experiences):
    """添加关系"""
    
    relations = []
    
    # 风险关系
    relations.append({
        "source": "task",
        "target": "risk",
        "relation": "has_risk",
        "properties": {
            "level": snapshot.orchestration.risk.level
        }
    })
    
    # 经验关系
    for experience in experiences["experiences"]:
        relations.append({
            "source": "task",
            "target": f"experience_{experience['category']}",
            "relation": "produced",
            "properties": {
                "category": experience["category"]
            }
        })
    
    return relations
```

### L3 学习报告（Learning Report）

```python
def generate_learning_report(snapshot, experiences, graph):
    """生成学习报告"""
    
    report = {
        "status": "completed",
        "generated_at": "<ISO8601>",
        "task_summary": {
            "intent": snapshot.orchestration.intent.primary,
            "risk": snapshot.orchestration.risk.level,
            "route": snapshot.orchestration.route,
            "duration": calculate_duration(snapshot.meta.created_at, snapshot.meta.updated_at)
        },
        "experiences": experiences,
        "knowledge_graph": graph,
        "recommendations": generate_recommendations(snapshot, experiences)
    }
    
    return report
```

**生成建议**：
```python
def generate_recommendations(snapshot, experiences):
    """生成建议"""
    
    recommendations = []
    
    # 基于意图的建议
    if snapshot.orchestration.intent.primary == "diagnose_fix":
        recommendations.append({
            "type": "diagnosis",
            "content": "建立诊断知识图谱，快速定位根因"
        })
    
    if snapshot.orchestration.intent.primary == "feature_dev":
        recommendations.append({
            "type": "feature_dev",
            "content": "建立功能开发最佳实践库"
        })
    
    # 基于风险的建议
    if snapshot.orchestration.risk.level == "high":
        recommendations.append({
            "type": "risk_management",
            "content": "加强高风险任务的风险控制"
        })
    
    # 基于经验的建议
    for experience in experiences["experiences"]:
        if experience["content"]["lessons_learned"]:
            for lesson in experience["content"]["lessons_learned"]:
                recommendations.append({
                    "type": "lesson",
                    "content": lesson["content"]
                })
    
    return recommendations
```

## 输出契约
- `snapshot.learning`（`experiences` / `knowledge_graph` / `recommendations`）
- 学习报告文件，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 经验提取失败 → 降级为手动提取，标注 `manual: true`
- 知识图谱构建失败 → 跳过图谱，仅记录经验
- 学习报告生成失败 → 记录日志，不影响任务

## 何时升级
- 经验提取失败 → `pax-council`
- 需要用户确认 → 返回上游阶段
- 知识图谱异常 → `pax-diagnose`