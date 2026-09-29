---
name: pax-plan
description: >
  将已澄清/诊断的目标转化为机器可冻结的任务计划。当共识收敛且门禁通过，需要产出可执行、可回滚的 `plan` 区时使用。
version: 0.2.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-plan

## Execution Contract
- 前置门禁：`consensus.gaps_remaining == []`；诊断类任务额外要求 `diagnosis.status == settled` 且 `diagnosis.root_cause.confidence >= medium`
- 未通过门禁：拒绝冻结，返回澄清或诊断阶段
- 版本检查：`pax-ops/versions.json`
- 禁止在门禁不通过时冻结计划
- 计划冻结后（`plan.status == frozen`）不得就地修改，需重新协商

## 职责边界
- 做什么：将已澄清/诊断的目标转化为机器可冻结的任务计划
- 不做什么：不执行动作、不做共识收敛、不做独立评审

## 输入
- 必需：`snapshot.consensus`
- 可选：`snapshot.diagnosis`（诊断类任务必需）、`snapshot.contract`

## 工作流

### P1 门禁校验（Gate Check）

```python
def check_gate(snapshot):
    """校验前置门禁"""
    
    # 条件 1: 共识无缺口
    if snapshot.consensus.gaps_remaining:
        return False, f"存在 {len(snapshot.consensus.gaps_remaining)} 个未解决缺口"
    
    # 条件 2: 诊断类任务要求诊断完成
    if snapshot.orchestration.diagnose_required:
        if not snapshot.diagnosis:
            return False, "诊断任务缺少 diagnosis 区"
        if snapshot.diagnosis.status != "settled":
            return False, f"诊断状态为 {snapshot.diagnosis.status}，需要 settled"
        if snapshot.diagnosis.root_cause.confidence < "medium":
            return False, f"根因置信度 {snapshot.diagnosis.root_cause.confidence}，需要 >= medium"
    
    # 条件 3: 契约已确认
    if not snapshot.contract.authorization.confirmed:
        return False, "契约未确认"
    
    return True, "门禁通过"
```

### P2 步骤分解（Step Decomposition）

**分解原则**：
1. 每个步骤必须可独立执行和验证
2. 步骤粒度：15-60 分钟可完成
3. 每个步骤绑定明确的输入和输出
4. 标注依赖关系（`depends_on`）

**分解算法**：
```python
def decompose_steps(snapshot):
    """将目标分解为步骤"""
    
    steps = []
    goal = snapshot.goal.statement
    
    # 根据意图类型选择分解策略
    if snapshot.orchestration.intent.primary == "diagnose_fix":
        steps = decompose_fix_steps(snapshot.diagnosis)
    elif snapshot.orchestration.intent.primary == "data_ops":
        steps = decompose_data_ops_steps(snapshot)
    elif snapshot.orchestration.intent.primary == "feature_dev":
        steps = decompose_feature_steps(snapshot)
    elif snapshot.orchestration.intent.primary == "refactor":
        steps = decompose_refactor_steps(snapshot)
    elif snapshot.orchestration.intent.primary == "tool_build":
        steps = decompose_tool_steps(snapshot)
    else:
        steps = decompose_generic_steps(snapshot)
    
    return steps
```

**诊断修复分解**：
```yaml
steps:
  - id: S1
    action: "修复根因代码"
    inputs: [diagnosis.root_cause.statement]
    outputs: [代码变更]
    depends_on: []
    rollback: "git revert"
    effort: "15-30min"
    risk: medium
    
  - id: S2
    action: "编写回归测试"
    inputs: [diagnosis.minimal_repro]
    outputs: [测试文件]
    depends_on: [S1]
    rollback: "删除测试文件"
    effort: "15-30min"
    risk: low
    
  - id: S3
    action: "运行回归测试"
    inputs: [测试文件]
    outputs: [测试结果]
    depends_on: [S2]
    rollback: "无需回滚"
    effort: "5-10min"
    risk: low
    
  - id: S4
    action: "数据订正（如需要）"
    inputs: [diagnosis.regression_scope]
    outputs: [订正脚本, 订正报告]
    depends_on: [S1]
    rollback: "回滚脚本"
    effort: "30-60min"
    risk: high
    # 数据订正专用字段：
    prerequisite: storage_backend_confirmed
    script_language: "mongosh|sql|python"
```

**功能开发分解**：
```yaml
steps:
  - id: S1
    action: "实现核心逻辑"
    inputs: [goal, success_criteria]
    outputs: [代码变更]
    depends_on: []
    rollback: "git revert"
    effort: "30-60min"
    risk: medium
    
  - id: S2
    action: "编写单元测试"
    inputs: [success_criteria]
    outputs: [测试文件]
    depends_on: [S1]
    rollback: "删除测试文件"
    effort: "15-30min"
    risk: low
    
  - id: S3
    action: "集成测试"
    inputs: [代码变更, 测试文件]
    outputs: [测试结果]
    depends_on: [S2]
    rollback: "无需回滚"
    effort: "15-30min"
    risk: medium
    
  - id: S4
    action: "更新文档"
    inputs: [代码变更]
    outputs: [文档变更]
    depends_on: [S3]
    rollback: "git revert"
    effort: "15-30min"
    risk: low
```

### P3 风险标注（Risk Annotation）

每个步骤必须标注风险等级：

| 风险 | 条件 | 要求 |
|------|------|------|
| `low` | 可轻易回滚，无外部依赖 | 无需额外审批 |
| `medium` | 需要协调，部分可回滚 | 需要 code review |
| `high` | 不可逆或高影响 | 需要用户确认 + `pax-verify` 验证 |

**风险维度**：
```yaml
risk_assessment:
  irreversibility: 1-3    # 1=可轻易回滚, 3=不可逆
  impact_scope: 1-3       # 1=单模块, 3=系统级
  uncertainty: 1-3        # 1=明确, 3=高度不确定
  coordination_cost: 1-3  # 1=单人, 3=跨团队
  total: 4-12
  level: low | medium | high
```

### P4 回退策略（Rollback Strategy）

每个步骤必须定义回退方案：

| 回退类型 | 条件 | 方案 |
|----------|------|------|
| `git_revert` | 代码变更 | `git revert <commit>` |
| `delete_file` | 新增文件 | 删除文件 |
| `config_revert` | 配置变更 | 恢复备份配置 |
| `data_rollback` | 数据变更 | 执行回滚脚本 |
| `none` | 无需回滚 | 验证步骤、文档更新 |

**回退约束**：
- 数据变更步骤必须提供可执行的回滚脚本
- 跨仓库步骤必须标注各仓库的回滚方案
- 高风险步骤的回滚方案必须经过验证

### P5 验证策略（Verification Strategy）

每个步骤必须定义验证方法和通过标准：

```yaml
verification_strategy:
  - step: S1
    method: "单元测试"
    criteria: "所有测试通过"
    tools: ["pytest"]
    timeout: "5min"
    
  - step: S2
    method: "代码审查"
    criteria: "无阻塞性问题"
    tools: ["git diff"]
    timeout: "15min"
    
  - step: S4
    method: "数据验证"
    criteria: "订正后数据一致性检查通过"
    tools: ["sql", "mongosh"]
    timeout: "10min"
    # 数据订正专用：
    rollback_verified: true  # 回滚方案已验证
```

### P6 跨仓库标注（Cross-Repo Annotation）

当 `orchestration.annotations.cross_repo == true` 时：

```yaml
steps:
  - id: S1
    action: "修复后端逻辑"
    repo: "ops-monitor"
    execution_strategy: "subagent"  # subagent | separate_session | manual_handoff
    rollback: "git revert in ops-monitor"
    
  - id: S2
    action: "更新前端界面"
    repo: "ops-pilot-web"
    execution_strategy: "manual_handoff"
    rollback: "git revert in ops-pilot-web"
```

**执行策略**：

| 策略 | 适用场景 | 要求 |
|------|----------|------|
| `subagent` | 可独立执行，无交互 | 自动执行，无需用户介入 |
| `separate_session` | 需要独立会话，但可自动 | 新开会话执行 |
| `manual_handoff` | 需要用户确认或手动操作 | 用户手动确认 |

### P7 计划冻结（Plan Freeze）

```python
def freeze_plan(steps, verification_strategy):
    """冻结计划"""
    
    # 最终校验
    for step in steps:
        # 检查回滚方案
        if step.risk == "high" and not step.rollback:
            return False, f"步骤 {step.id} 高风险但无回滚方案"
        
        # 检查数据订正前置条件
        if step.prerequisite == "storage_backend_confirmed":
            if not step.script_language:
                return False, f"步骤 {step.id} 数据订正缺少 script_language"
        
        # 检查跨仓库标注
        if step.repo:
            if not step.execution_strategy:
                return False, f"步骤 {step.id} 跨仓库步骤缺少 execution_strategy"
    
    # 写入快照
    plan = {
        "steps": steps,
        "dependencies": calculate_dependencies(steps),
        "evidence": collect_evidence(steps),
        "verification_strategy": verification_strategy,
        "status": "frozen",
        "frozen_at": "<ISO8601>",
        "frozen_by": "pax-plan"
    }
    
    return True, plan
```

## 输出契约
- `snapshot.plan`（`status: frozen`）与 `plan_summary.md`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 快照缺失 → 降级为独立模式，自行初始化最小快照
- 门禁不通过 → 拒绝冻结，返回上游阶段
- 计划无法收敛 → 升级 `pax-council`

## 何时升级
- 门禁不通过 → 返回上游阶段
- 计划无法收敛或高风险 → `pax-council`
- 需要独立评审 → `pax-review`
- 需要环境事实或独立运行 → `pax-worker-*`
