---
name: pax-docs
description: >
    Use when: 把已确认硬决策沉淀为 CONTEXT.md 与 ADR。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 1.0.0
family: pax
layer: L4
optional: true
requires_snapshot: true
---

# pax-docs


## Overview

文档沉淀 Skill。把执行留痕沉淀为可查的文档 / 决策记录 / 案例库。

## When to Use

任务完成、评审通过、或需要归档一次执行时。

## Common Pitfalls

- 文档过于冗长，无法追溯关键决策。
- 与既有文档重复。
- 未建立索引。

## Verification Checklist

- [ ] 文档结构统一，含关键决策与证据
- [ ] 已建立 / 更新索引
- [ ] 文档链接到相关快照与版本
## Execution Contract
- 前置门禁：可被任意 L0/L1/L2 调用；输入为已确认的硬决策或已产出的经验条目
- 未通过门禁：返回 `blocked`
- 版本检查：`pax-ops/versions.json`
- 增量写入，不污染正式文档
- 草稿区与正式区分离
- 最后统一审核后合并
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：把已确认硬决策沉淀为 `CONTEXT.md` 与 ADR
- 不做什么：不认领路由落点、不改变主流程、不覆盖既有正式文档

## 输入
- 必需：快照中已确认的硬决策或经验条目
- 可选：目标文档路径、ADR 编号、作者信息

## 工作流

### D1 决策提取（Decision Extraction）

从快照中提取已确认的硬决策：

```python
def extract_decisions(snapshot):
    """提取已确认硬决策"""
    
    decisions = []
    
    # 从 diagnosis 提取
    if snapshot.diagnosis and snapshot.diagnosis.root_cause:
        decisions.append({
            "id": f"D{len(decisions) + 1}",
            "type": "root_cause",
            "statement": snapshot.diagnosis.root_cause.statement,
            "confidence": snapshot.diagnosis.root_cause.confidence,
            "severity": snapshot.diagnosis.root_cause.severity,
            "source": "diagnosis"
        })
    
    # 从 plan 提取
    if snapshot.plan:
        for step in snapshot.plan.steps:
            if step.outputs:
                decisions.append({
                    "id": f"D{len(decisions) + 1}",
                    "type": "plan_decision",
                    "statement": step.action,
                    "source": "plan",
                    "step_id": step.id
                })
    
    # 从 execution 提取
    if snapshot.execution:
        for change in snapshot.execution.changes:
            decisions.append({
                "id": f"D{len(decisions) + 1}",
                "type": "implementation",
                "statement": change.summary,
                "source": "execution",
                "file": change.file
            })
    
    # 从 review 提取
    if snapshot.review:
        for finding in snapshot.review.findings:
            if finding.severity in ("blocker", "major"):
                decisions.append({
                    "id": f"D{len(decisions) + 1}",
                    "type": "review_finding",
                    "statement": finding.description,
                    "source": "review"
                })
    
    return decisions
```

### D2 CONTEXT.md 草稿（CONTEXT.md Draft）

**CONTEXT.md 结构**：
```markdown
# Project Context

## 当前状态
- 版本：v0.1.0
- 最后更新：2026-09-29

## 关键决策

### [D1] CMDB 字段校验修复
- **决策**：修复时间类型字段的正则表达式校验逻辑
- **原因**：校验代码未区分字段类型，对时间字段执行了正则校验
- **影响**：修复后时间类型字段可正常填写
- **来源**：diagnosis (2026-09-29)
- **关联**：ADR-001

### [D2] 数据订正方案
- **决策**：使用 mongosh 脚本订正 500 条错误记录
- **原因**：CMDB 使用 MongoDB，需要匹配存储后端
- **影响**：订正后数据一致性恢复
- **来源**：plan (S4)
- **关联**：ADR-002

## 经验条目

### [E1] 数据订正前必须确认存储后端
- **场景**：数据订正任务
- **教训**：未确认存储后端就写 MySQL 脚本，实际是 MongoDB
- **建议**：D2 阶段强制确认存储后端、ORM、迁移工具

## 待办
- [ ] 补充更多经验条目
```

**增量写入规则**：
1. 不覆盖既有内容
2. 追加到对应章节
3. 保留时间戳和来源
4. 冲突时保留草稿，请求人工裁决

### D3 ADR 草稿（ADR Draft）

**ADR 结构**（ADR-NNN.md）：
```markdown
# ADR-001: CMDB 字段校验修复

**日期**：2026-09-29
**状态**：Accepted
**决策者**：主流程, 规划阶段

## 背景

CMDB 模块的字段校验有问题，时间类型的字段填写后报错"字段不为设定的正则表达式"。

## 决策

修复时间类型字段的正则表达式校验逻辑，在校验前检查字段类型。

## 理由

1. 校验代码未区分字段类型，对时间字段执行了正则校验
2. 其他类型字段校验正常
3. 修复后不影响现有功能

## 影响

- 修复后时间类型字段可正常填写
- 不需要数据订正
- 不需要迁移

## 替代方案

- **方案 B**：在正则表达式中添加时间格式的匹配规则
  - 优点：不需要修改校验逻辑
  - 缺点：正则表达式会变得复杂，难以维护

- **方案 C**：禁用时间字段的正则校验
  - 优点：实现简单
  - 缺点：可能引入安全问题

## 关联

- Issue: #123
- PR: #124
- 相关 ADR: 无
```

**ADR 编号规则**：
- 格式：`ADR-NNN.md`（三位数字，从 001 开始）
- 自动递增，不重用已删除的编号
- 草稿区：`drafts/ADR-NNN.md`
- 正式区：`docs/adr/ADR-NNN.md`

### D4 草稿管理（Draft Management）

**目录结构**：
```
docs/
├── CONTEXT.md          # 正式区
├── adr/                # 正式区 ADR
│   ├── ADR-001.md
│   └── ADR-002.md
└── drafts/             # 草稿区
    ├── CONTEXT.md.draft
    └── adr/
        ├── ADR-003.md.draft
        └── ADR-004.md.draft
```

**草稿状态**：

| 状态 | 语义 | 操作 |
|------|------|------|
| `draft` | 草稿，未审核 | 可修改、可删除 |
| `review` | 待审核 | 需要人工审核 |
| `accepted` | 已接受 | 合并到正式区 |
| `rejected` | 已拒绝 | 删除或保留备查 |
| `superseded` | 已被替代 | 标记并指向新 ADR |

### D5 合并流程（Merge Process）

```python
def merge_to_formal(drafts):
    """合并草稿到正式区"""
    
    # 条件 1: 所有草稿必须经过审核
    for draft in drafts:
        if draft.status != "review":
            return False, f"草稿 {draft.id} 未审核"
    
    # 条件 2: 检查冲突
    conflicts = check_conflicts(drafts)
    if conflicts:
        return False, f"存在冲突: {conflicts}"
    
    # 合并
    for draft in drafts:
        merge_draft(draft)
    
    return True, "合并完成"
```

### D6 变更清单（Change List）

```yaml
docs_change_list:
  - type: CONTEXT.md
    action: append
    section: "关键决策"
    entries:
      - id: D1
        statement: "修复时间类型字段的正则表达式校验逻辑"
        source: diagnosis
      - id: D2
        statement: "使用 mongosh 脚本订正 500 条错误记录"
        source: plan
  - type: ADR
    action: create
    file: "docs/adr/ADR-001.md"
    status: accepted
  - type: ADR
    action: create
    file: "docs/adr/ADR-002.md"
    status: accepted
  - type: CONTEXT.md
    action: append
    section: "经验条目"
    entries:
      - id: E1
        statement: "数据订正前必须确认存储后端"
        source: trial_feedback
```

## 输出契约
- `CONTEXT.md` 增量块
- `ADR-<N>.md` 草稿或正式版
- 变更清单，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 硬决策缺失 → 返回 `blocked`
- 与既有正式文档冲突 → 保留草稿，请求人工裁决
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 高风险或涉及架构级文档冲突 → 请求人工审批
