---
name: pax-clarify
description: >
    Use when: 当用户目标模糊、需求不完整、或存在多种可能的理解时，需要澄清需求并收敛共识。包括功能开发、数据操作、工具构建等需要明确范围的场景。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。
version: 1.0.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-clarify


## Overview

共识状态机驱动的澄清 Skill。围绕 6 个共识维度 × 5 个状态，通过问题生成与前沿计算收敛模糊需求。

## When to Use

用户目标模糊、需求不完整、或存在多种可能理解；编排层判定需要澄清时进入。

## Common Pitfalls

- 一次问太多问题，用户回答质量下降。
- 未记录共识状态机状态，下游无法判断澄清是否收敛。
- 跳过存储后端 / 影响面等硬约束维度，直接进入执行。

## Verification Checklist

- [ ] 所有 6 个共识维度状态已更新，收敛维度达到目标精度
- [ ] 已生成并记录待澄清问题清单，标注优先级与预期答案
- [ ] 输出契约的澄清结果已写入快照，可以交给下游 Skill
## Execution Contract
- 前置门禁：快照已初始化，`orchestration.question_strategy` 已确定
- 未通过门禁：拒绝启动，返回用户补齐信息
- 版本检查：`pax-ops/versions.json`
- 禁止在 `frontier` 非空时冻结契约或进入下一阶段
- 禁止在 `consensus.gaps_remaining` 非空时进入 `pax-plan`
- 环境事实不得询问用户，必须调度 `pax-worker-*` 自动获取
- 每次提问必须对应设计树节点或共识维度缺口
- 禁止在用户未确认契约草稿时标记 `contract.confirmed == true`

## 职责边界
- 做什么：共识状态机、设计树维护、缺口检测、契约草稿
- 不做什么：不做任务分解、不执行动作、不产出执行日志、不做独立评审

## 输入
- 必需：`snapshot.orchestration`（含 `intent`、`route`、`question_strategy`、`risk`）
- 必需：`snapshot.goal.statement`
- 可选：历史快照、领域依赖映射（`references/domain-dependencies.md`）、参考文档

## 工作流

#### 维度键空间约定

设计树的 `dimension:` 字段一律使用 **6 个澄清短键**之一（与 `consensus.dimensions` 的键空间一致，
供 `update_dimension` 写入与 `detect_gaps` 读取）：

| 短键 | 完整快照路径（描述含义） | 适用设计树 |
|---|---|---|
| `goal` | `snapshot.goal.statement` | 全部 |
| `success_criteria` | `snapshot.goal.success_criteria` | 全部 |
| `constraints` | `snapshot.contract.constraints` | 全部 |
| `authorization` | `snapshot.contract.authorization` | 全部 |
| `exceptions` | `snapshot.contract.exceptions` | feature_dev / refactor / data_ops / diagnose_fix |
| `terminology` | `snapshot.goal.terminology` | feature_dev / refactor |

诊断/数据类设计树中的 `symptom.*` 与 `infrastructure.storage_backend` 节点**不**属于上述 6 个澄清维度——
它们写入 `snapshot.symptom` / `snapshot.infrastructure`（由 `pax-diagnose` 或 `pax-worker-*` 消费），
不更新 `consensus.dimensions`。这类节点的 `dimension:` 字段使用对应的完整路径（如 `symptom.description`），
并在 `update_dimension` 前判断：若短键不在 6 个澄清键中，则走 `snapshot.<section>.<field>` 直写路径，不写入 `consensus.dimensions`。

### W1 设计树初始化（Design Tree Initialization）

根据 `orchestration.intent.primary` 初始化不同的设计树模板。设计树节点按依赖关系组织，支持 `depends_on`（父依赖）和 `children`（子节点）。

#### 诊断修复类设计树（`diagnose_fix`）

```yaml
design_tree:
  - id: D1
    question: "问题的具体表现是什么？（错误信息、异常行为、影响范围）——对应 snapshot.symptom.description"
    status: frontier
    dimension: symptom.description
    depends_on: []
    children: [D2]
    
  - id: D2
    question: "这个问题首次出现的时间？最近有哪些变更？——对应 snapshot.symptom.first_observed"
    status: frontier
    dimension: symptom.first_observed
    depends_on: [D1]
    children: [D3]
    
  - id: D3
    question: "影响范围有多大？（影响哪些用户、模块、功能）——对应 snapshot.symptom.impact"
    status: frontier
    dimension: symptom.impact
    depends_on: [D2]
    children: [D4]
    
  - id: D4
    question: "修复的成功标准是什么？（什么情况下算修复完成）——对应 snapshot.goal.success_criteria"
    status: frontier
    dimension: success_criteria
    depends_on: [D3]
    children: [D5]
    
  - id: D5
    question: "有什么约束条件？（不可修改的模块、依赖限制、时间窗口）——对应 snapshot.contract.constraints"
    status: frontier
    dimension: constraints
    depends_on: [D4]
    children: [D6]
    
  - id: D6
    question: "修复的授权范围？（可以修改哪些文件/模块/配置）——对应 snapshot.contract.authorization"
    status: frontier
    dimension: authorization
    depends_on: [D5]
    children: [D7]
    
  - id: D7
    question: "是否有例外情况需要特殊处理？——对应 snapshot.contract.exceptions"
    status: frontier
    dimension: exceptions
    depends_on: [D6]
    children: []
```

#### 功能开发类设计树（`feature_dev`）

```yaml
design_tree:
  - id: D1
    question: "功能的核心目标是什么？（一句话描述）——对应 snapshot.goal.statement"
    status: frontier
    dimension: goal
    depends_on: []
    children: [D2]
    
  - id: D2
    question: "成功标准是什么？（可验证的验收条件）——对应 snapshot.goal.success_criteria"
    status: frontier
    dimension: success_criteria
    depends_on: [D1]
    children: [D3]
    
  - id: D3
    question: "有哪些约束条件？（技术栈、性能要求、兼容性）——对应 snapshot.contract.constraints"
    status: frontier
    dimension: constraints
    depends_on: [D2]
    children: [D4]
    
  - id: D4
    question: "开发授权范围？（可以创建/修改哪些模块）——对应 snapshot.contract.authorization"
    status: frontier
    dimension: authorization
    depends_on: [D3]
    children: [D5]
    
  - id: D5
    question: "有没有需要向后兼容的场景？——对应 snapshot.contract.exceptions"
    status: frontier
    dimension: exceptions
    depends_on: [D4]
    children: [D6]
    
  - id: D6
    question: "当前状态和边界条件是什么？——对应 snapshot.goal.terminology"
    status: frontier
    dimension: terminology
    depends_on: [D5]
    children: []
```

#### 重构优化类设计树（`refactor`）

```yaml
design_tree:
  - id: D1
    question: "重构的目标是什么？（性能、可读性、架构、可维护性）——对应 snapshot.goal.statement"
    status: frontier
    dimension: goal
    depends_on: []
    children: [D2]
    
  - id: D2
    question: "重构成功标准？（性能提升比例、代码行数减少、测试覆盖率）——对应 snapshot.goal.success_criteria"
    status: frontier
    dimension: success_criteria
    depends_on: [D1]
    children: [D3]
    
  - id: D3
    question: "什么不能改？（外部接口、数据结构、公共契约）——对应 snapshot.contract.constraints"
    status: frontier
    dimension: constraints
    depends_on: [D2]
    children: [D4]
    
  - id: D4
    question: "授权范围？（可以修改哪些文件/模块）——对应 snapshot.contract.authorization"
    status: frontier
    dimension: authorization
    depends_on: [D3]
    children: []
```

#### 数据操作类设计树（`data_ops`）

```yaml
design_tree:
  - id: D1
    question: "数据问题的具体表现？（数据不一致、字段错误、数据丢失）——对应 snapshot.symptom.description"
    status: frontier
    dimension: symptom.description
    depends_on: []
    children: [D2]
    
  - id: D2
    question: "数据规模和影响范围？（多少条记录、多少用户、哪些模块）——对应 snapshot.symptom.impact"
    status: frontier
    dimension: symptom.impact
    depends_on: [D1]
    children: [D3]
    
  - id: D3
    question: "存储后端确认？（MongoDB / MySQL / PostgreSQL / 其他）——对应 snapshot.infrastructure.storage_backend"
    status: frontier
    dimension: infrastructure.storage_backend
    depends_on: [D2]
    children: [D4]
    requires_worker: true
    
  - id: D4
    question: "订正的成功标准？（数据一致性校验、回归测试通过）——对应 snapshot.goal.success_criteria"
    status: frontier
    dimension: success_criteria
    depends_on: [D3]
    children: [D5]
    
  - id: D5
    question: "约束条件？（不可删除的记录、需要保留的审计轨迹、时间窗口）——对应 snapshot.contract.constraints"
    status: frontier
    dimension: constraints
    depends_on: [D4]
    children: [D6]
    
  - id: D6
    question: "授权范围？（可以修改哪些集合/表/字段）——对应 snapshot.contract.authorization"
    status: frontier
    dimension: authorization
    depends_on: [D5]
    children: [D7]
    
  - id: D7
    question: "异常处理方案？（订正失败的回滚策略）——对应 snapshot.contract.exceptions"
    status: frontier
    dimension: exceptions
    depends_on: [D6]
    children: []
```

#### 文档咨询类设计树（`doc_consult`）

```yaml
design_tree:
  - id: D1
    question: "咨询的具体问题是什么？（一句话描述）——对应 snapshot.goal.statement"
    status: frontier
    dimension: goal
    depends_on: []
    children: [D2]
    
  - id: D2
    question: "期望的输出形式？（文档、方案、解释、对比）——对应 snapshot.goal.success_criteria"
    status: frontier
    dimension: success_criteria
    depends_on: [D1]
    children: []
```

#### 工具构建类设计树（`tool_build`）

```yaml
design_tree:
  - id: D1
    question: "工具的核心功能是什么？（一句话描述）——对应 snapshot.goal.statement"
    status: frontier
    dimension: goal
    depends_on: []
    children: [D2]
    
  - id: D2
    question: "输入输出是什么？（接受什么输入、产出什么输出）——对应 snapshot.goal.success_criteria"
    status: frontier
    dimension: success_criteria
    depends_on: [D1]
    children: [D3]
    
  - id: D3
    question: "运行环境要求？（Python/Node/Shell、依赖库）——对应 snapshot.contract.constraints"
    status: frontier
    dimension: constraints
    depends_on: [D2]
    children: [D4]
    
  - id: D4
    question: "授权范围？（可以访问哪些文件系统/网络/API）——对应 snapshot.contract.authorization"
    status: frontier
    dimension: authorization
    depends_on: [D3]
    children: []
```

### W2 共识维度引擎（Consensus Dimension Engine）

六个共识维度，每个维度有独立的状态机。维度状态驱动 `required_precision` 的达成检测。

#### 维度定义

| 维度 | 标识 | 含义 | 最低目标状态 |
|---|---|---|---|
| 目标 | `goal` | 用户目标的清晰度和完整性 | `confirmed` |
| 成功标准 | `success_criteria` | 可验证的验收条件 | `confirmed` |
| 约束条件 | `constraints` | 技术、时间、范围限制 | `confirmed` |
| 授权范围 | `authorization` | 可以修改/创建/删除的范围 | `confirmed` |
| 例外情况 | `exceptions` | 边界条件、特殊处理、回滚方案 | `confirmed` |
| 术语定义 | `terminology` | 关键术语的定义和边界 | `fuzzy` |

#### 维度状态机

```text
unknown → fuzzy → assumption → confirmed → locked
  ↑         ↑        ↑          ↑         ↑
  未讨论    有模糊    有假设     已确认     已锁定（不可变）
  的维度    理解      但未验证   的状态     状态
```

| 状态 | 语义 | 是否可冻结契约 |
|---|---|---|
| `unknown` | 未讨论，无任何信息 | 否 |
| `fuzzy` | 有模糊理解，但未明确 | 否 |
| `assumption` | 有假设但未验证 | 否 |
| `confirmed` | 已确认，有用户明确回答 | 是 |
| `locked` | 已锁定，不可再修改 | 是 |

#### 精度要求映射

| `required_precision` | 必须达到的维度状态 |
|---|---|
| `low` | `goal` ≥ `confirmed`，`success_criteria` ≥ `confirmed` |
| `medium` | `goal` / `success_criteria` / `constraints` ≥ `confirmed`，`authorization` ≥ `confirmed` |
| `high` | 所有维度 ≥ `confirmed`，`exceptions` ≥ `confirmed`，`terminology` ≥ `confirmed` |

#### 维度状态更新规则

```python
def update_dimension(dimension, user_answer, current_state, consensus, snapshot=None):
    """根据用户回答更新维度状态。

    如果 dimension 是 6 个澄清短键之一（goal / success_criteria / constraints /
    authorization / exceptions / terminology），写入 `consensus.dimensions[dimension]`，
    供 `detect_gaps` 读取。

    如果 dimension 是完整快照路径（如 `symptom.description` / `infrastructure.storage_backend`），
    则写入对应的 `snapshot.<section>.<field>`，不更新 `consensus.dimensions`。
    """
    
    CLARIFY_DIMENSIONS = {"goal", "success_criteria", "constraints", "authorization", "exceptions", "terminology"}
    
    # 非澄清维度：写入 snapshot.<section>.<field>，不更新 consensus.dimensions
    if dimension not in CLARIFY_DIMENSIONS and snapshot is not None:
        section, _, field = dimension.partition(".")
        if section and field and hasattr(snapshot, section):
            setattr(snapshot, section, {**getattr(snapshot, section, {}), field: user_answer})
        return "confirmed"
    
    # 澄清维度：更新状态
    if current_state == "locked":
        return "locked"  # 不可变
    
    # 有明确回答 → confirmed
    if is_explicit_answer(user_answer):
        return "confirmed"
    
    # 有默认假设 → assumption
    if has_default_assumption(dimension, user_answer):
        return "assumption"
    
    # 有模糊回答 → fuzzy
    if is_vague_answer(user_answer):
        return "fuzzy"
    
    # 无回答 → 保持原状态
    return current_state
```

### W3 前沿计算（Frontier Calculation）

```python
def calculate_frontier(design_tree):
    """计算设计树前沿：所有 depends_on 已 settled 的未决节点"""
    
    settled_ids = {node.id for node in design_tree if node.status == "settled"}
    
    frontier = []
    for node in design_tree:
        if node.status == "settled":
            continue
        # 检查所有依赖是否已 settled
        if all(dep in settled_ids for dep in node.depends_on):
            node.status = "frontier"
            frontier.append(node)
        else:
            node.status = "blocked"
    
    return frontier
```

### W4 问题生成（Question Generation）

#### 问题生成规则

```python
def generate_questions(frontier, strategy, context):
    """从前沿节点生成问题列表"""
    
    questions = []
    for node in frontier:
        q = {
            "id": node.id,
            "question": node.question,
            "dimension": node.dimension,
            "suggested_answer": suggest_answer(node, context),
            "priority": calculate_priority(node, context),
            "requires_worker": node.get("requires_worker", False)
        }
        questions.append(q)
    
    # 排序：阻塞性 > 优化性 > 可后置
    questions.sort(key=lambda q: (-q["priority"], q["id"]))
    
    if strategy == "batch":
        return questions
    else:  # one-by-one
        return [questions[0]]  # 只返回最高优先级的一个
```

#### 推荐答案生成

```python
def suggest_answer(node, context):
    """为每个问题生成推荐答案"""
    
    # 环境事实类问题 → 标记为自动获取
    if node.get("requires_worker"):
        return "<自动获取：调度 pax-worker-*>"
    
    # 有默认假设 → 返回默认值 + 风险标注
    if has_default_assumption(node.dimension, context):
        default = get_default_assumption(node.dimension, context)
        return f"{default}（默认假设，如有不同请告知）"
    
    # 无默认 → 返回开放问题
    return "<需要用户回答>"
```

#### 优先级计算

| 优先级 | 条件 | 值 |
|---|---|---|
| 阻塞性 | 问题不回答则后续所有步骤无法进行 | 3 |
| 优化性 | 问题不回答则质量下降但可继续 | 2 |
| 可后置 | 问题可延后到执行阶段再回答 | 1 |

#### 问题选择原则

1. **只问能改变行动的问题**：如果答案不会改变后续执行路径，不提问
2. **默认假设优先**：优先使用"默认假设 + 风险标注"，而非开放式提问
3. **阻塞性优先**：阻塞性问题必须问，优化性问题给默认值，可后置问题写入待办
4. **一次一问**：`one-by-one` 模式下每次只问一个，避免信息过载
5. **批量提问**：`batch` 模式下一次性输出所有前沿问题，附推荐答案

### W5 环境事实协议（Environment Fact Protocol）

环境事实是可以通过工具/命令自动获取的信息，不应询问用户。

#### 环境事实类型

| 类型 | 标识 | 示例 | 获取方式 |
|---|---|---|---|
| 存储后端 | `storage_backend` | MongoDB / MySQL / PostgreSQL | 检查 `pom.xml` / `package.json` / 配置文件 |
| ORM 层 | `orm` | JPA / MyBatis / MongoPlus | 检查依赖和注解 |
| 迁移工具 | `migration_tool` | Flyway / Liquibase / mongosh | 检查 `migration/` 或 `script/` 目录 |
| 依赖版本 | `dependency_version` | 库版本、框架版本 | 检查 `pom.xml` / `package.json` / `requirements.txt` |
| 运行环境 | `runtime_env` | Java / Node / Python 版本 | `java -version` / `node --version` |
| 现有脚本 | `existing_scripts` | 数据订正脚本目录结构 | `ls script/` 或 `ls migration/` |
| 分支状态 | `git_branch` | 当前分支、是否有未提交变更 | `git status` / `git branch` |

#### 调度协议

```python
def retrieve_environment_fact(fact_type, context):
    """调度 pax-worker-* 获取环境事实"""
    
    # 根据事实类型选择 worker
    if fact_type in ("storage_backend", "orm", "migration_tool"):
        worker = "pax-worker-research"
        task = f"检查 {context.get('repo', '')} 的存储后端、ORM 和迁移工具"
    
    elif fact_type in ("dependency_version", "runtime_env"):
        worker = "pax-worker-research"
        task = f"检查 {context.get('repo', '')} 的依赖版本和运行环境"
    
    elif fact_type in ("existing_scripts", "git_branch"):
        worker = "pax-worker-research"
        task = f"检查 {context.get('repo', '')} 的脚本目录和分支状态"
    
    else:
        return None  # 未知类型，降级为询问用户
    
    # 返回调度指令，由上层执行
    return {
        "worker": worker,
        "task": task,
        "fact_type": fact_type
    }
```

#### 环境事实缓存

同一会话内已获取的环境事实应缓存，避免重复调度：

```python
env_facts_cache = {}  # {fact_type: {value, source, timestamp}}

def get_environment_fact(fact_type):
    """获取环境事实，优先从缓存读取"""
    if fact_type in env_facts_cache:
        return env_facts_cache[fact_type]
    
    result = retrieve_environment_fact(fact_type)
    if result:
        env_facts_cache[fact_type] = result
        return result
    return None
```

### W6 缺口检测（Gap Detection）

```python
def detect_gaps(consensus, required_precision):
    """检测剩余缺口"""
    
    gaps = []
    
    # 检查每个维度是否达到 required_precision 的目标状态
    target_states = get_target_states(required_precision)
    for dim_name, target_state in target_states.items():
        current_state = consensus.dimensions.get(dim_name, "unknown")
        if state_below(current_state, target_state):
            gaps.append({
                "dimension": dim_name,
                "current": current_state,
                "required": target_state,
                "reason": f"维度 '{dim_name}' 状态为 '{current_state}'，需要达到 '{target_state}'"
            })
    
    # 检查设计树是否有未决节点
    unsettled = [node for node in consensus.design_tree if node.status not in ("settled", "skipped")]
    if unsettled:
        gaps.append({
            "dimension": "design_tree",
            "current": f"{len(unsettled)} 个未决节点",
            "required": "0 个未决节点",
            "reason": f"设计树仍有 {len(unsettled)} 个未决节点"
        })
    
    return gaps
```

#### 缺口类型

| 类型 | 条件 | 处理方式 |
|---|---|---|
| 维度缺口 | 维度状态未达到 required_precision 目标 | 生成对应问题，加入前沿 |
| 设计树缺口 | 存在未决节点 | 计算前沿，生成问题 |
| 矛盾缺口 | 用户回答与已有信息矛盾 | 标记冲突，请求澄清 |
| 模糊缺口 | 用户回答模糊，未明确确认 | 标记为 assumption，标注风险 |

### W7 契约草稿（Contract Drafting）

当所有缺口检测为空且维度达到目标状态时，生成契约草稿。

```yaml
contract:
  authorization:
    scope: "<可以修改的范围>"
    files: ["<文件路径列表>"]
    modules: ["<模块列表>"]
    permissions: ["<权限列表>"]
    confirm_required: true  # 需要用户显式确认
    confirmed: false       # 用户确认状态
  
  constraints:
    - type: "technical"    # technical | temporal | scope | dependency
      description: "<约束描述>"
      source: "user"       # user | inferred | domain_map
      priority: "must"     # must | should | could
    - type: "temporal"
      description: "<时间约束>"
      source: "user"
      priority: "must"
  
  exceptions:
    - trigger: "<触发条件>"
      action: "<处理动作>"
      rollback: "<回滚方案>"
      confirmed: false
  
  assumptions:
    - statement: "<假设陈述>"
      confidence: "high"   # high | medium | low
      risk_if_wrong: "<如果假设错误的风险>"
      verified: false      # 是否已验证
  
  withdraw:
    - condition: "<撤回条件>"
      action: "<撤回动作>"
      impact: "<撤回影响>"
```

#### 契约确认流程

```python
def confirm_contract(contract_draft, user):
    """契约确认流程"""
    
    # 展示契约草稿给用户
    display = format_contract_for_display(contract_draft)
    
    # 请求用户确认
    confirmed = ask_user_to_confirm(display)
    
    if confirmed:
        contract_draft["authorization"]["confirmed"] = True
        contract_draft["authorization"]["confirmed_at"] = "<ISO8601>"
        contract_draft["withdraw"].extend(generate_withdraw_conditions(contract_draft))
        return contract_draft
    else:
        # 用户拒绝，需要修改
        return None  # 返回 None 表示需要继续澄清
```

#### 撤回条件生成

```python
def generate_withdraw_conditions(contract):
    """根据约束和假设生成撤回条件"""
    
    conditions = []
    
    # 基于约束的撤回
    for constraint in contract["constraints"]:
        if constraint["priority"] == "must":
            conditions.append({
                "condition": f"约束 '{constraint['description']}' 无法满足",
                "action": "暂停执行，返回规划阶段",
                "impact": "需要重新评估目标和方案"
            })
    
    # 基于假设的撤回
    for assumption in contract["assumptions"]:
        if assumption["confidence"] in ("medium", "low"):
            conditions.append({
                "condition": f"假设 '{assumption['statement']}' 被证伪",
                "action": "暂停执行，返回诊断/澄清阶段",
                "impact": assumption["risk_if_wrong"]
            })
    
    return conditions
```

### W8 收敛判定（Convergence Check）

```python
def check_convergence(consensus, design_tree, gaps):
    """检查是否达到收敛条件"""
    
    # 条件 1: 设计树前沿为空
    if design_tree and any(node.status == "frontier" for node in design_tree):
        return False, "存在未决前沿节点"
    
    # 条件 2: 所有维度达到 required_precision 目标
    if gaps:
        return False, f"存在 {len(gaps)} 个剩余缺口"
    
    # 条件 3: 所有阻塞性节点已 settled
    blocked = [node for node in design_tree if node.status == "blocked"]
    if blocked:
        return False, f"存在 {len(blocked)} 个阻塞节点（依赖未满足）"
    
    return True, "收敛完成"
```

## 主循环（Main Loop）

```python
def clarify(snapshot, user):
    """pax-clarify 主循环"""
    
    # 初始化
    design_tree = init_design_tree(snapshot.orchestration.intent.primary)
    consensus = init_consensus(snapshot.orchestration.risk.precision)
    env_cache = {}
    
    while True:
        # 计算前沿
        frontier = calculate_frontier(design_tree)
        
        # 检查收敛
        gaps = detect_gaps(consensus, snapshot.orchestration.risk.precision)
        converged, reason = check_convergence(consensus, design_tree, gaps)
        if converged:
            break
        
        # 生成问题
        questions = generate_questions(frontier, snapshot.orchestration.question_strategy, env_cache)
        
        # 处理环境事实类问题
        for q in questions:
            if q["requires_worker"]:
                fact = get_environment_fact(q["fact_type"])
                if fact:
                    mark_node_settled(design_tree, q["id"], fact["value"])
                    update_dimension(consensus, q["dimension"], fact["value"])
        
        # 过滤已自动获取的问题
        user_questions = [q for q in questions if not q["requires_worker"]]
        
        if not user_questions:
            continue  # 全部自动获取，继续循环
        
        # 向用户提问
        if snapshot.orchestration.question_strategy == "batch":
            answers = ask_user_batch(user_questions)
        else:
            answer = ask_user_one(user_questions[0])
            answers = {user_questions[0]["id"]: answer}
        
        # 记录答案，更新设计树和维度
        for q_id, answer in answers.items():
            node = find_node(design_tree, q_id)
            mark_node_settled(design_tree, q_id, answer)
            update_dimension(consensus, node.dimension, answer)
            reshape_design_tree(design_tree)  # 解锁后续节点
        
        # 检查用户疲劳
        if detect_user_fatigue():
            snapshot.orchestration.question_strategy = "batch"
    
    # 生成契约草稿
    contract = generate_contract_draft(consensus, design_tree)
    
    # 请求用户确认
    if not confirm_contract(contract, user):
        # 用户拒绝，需要继续澄清
        return clarify(snapshot, user)  # 递归
    
    return {
        "consensus": consensus,
        "contract": contract,
        "settled_at": "<ISO8601>"
    }
```

## 输出契约
- `snapshot.consensus`（`dimensions` / `design_tree` / `gaps_remaining` / `settled_at`）
- `snapshot.contract` 草稿（`authorization` / `constraints` / `exceptions` / `assumptions` / `withdraw`），格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 用户回答矛盾 → 标记冲突，请求澄清；连续 2 次矛盾则升级决策层
- 用户疲劳 → 自动降级为 `batch` 模式，减少轮次
- 无法收敛（超过 5 轮仍有缺口） → 升级决策层
- 用户拒绝提供信息 → 使用保守默认值并标注 `confidence: low`
- 环境事实获取失败 → 降级为询问用户，但标注 `source: user_inferred`
- 契约草稿被用户拒绝 → 返回澄清循环，标记被拒绝的维度为 `fuzzy`

## 何时升级
- 无法收敛或高风险决策 → 升级决策层
- 需要环境事实 → 调度 `pax-worker-*` 自动获取
- 需要独立评审 → 交由 `pax-review`（在 `pax-execute` 之后）
- 检测到架构级问题 → 升级决策层
- 用户连续 2 次回答矛盾 → 升级决策层
## 手工经验条目（历史 SkillOpt 关键词命中产物，未经验证）

<!-- 原 SkillOpt Cue Map，由 evals/skillopt/train_pax_offline.py 生成。
     SkillOpt 训练为 dry_run=true（奖励=关键词覆盖率），非真训练。
     以下条目为历史关键词命中产物，未经真实训练验证，仅作参考。 -->

- **clarify_storage_backend**: DBMS类型；持久层技术栈；存储介质
- **clarify_performance_impact**: 性能影响评估；SLA退化；响应时间阈值
- **clarify_root_cause**: 根因假设；根因收敛方向；根因排查切入点
- **clarify_error_scope**: 澄清错误作用域；影响面范围；错误边界确认
- **clarify_export_format**: 导出格式选择；字段映射；文件类型确认
- **clarify_approval_levels**: 审批层级数；驳回条件；审批人角色
- **clarify_correction_rules**: 订正规则确认；数据一致性约束；数据修补
- **clarify_migration_strategy**: 迁移策略选择；双写窗口；灰度切换
- **clarify_cleanup_criteria**: 清理条件；过期阈值；回收策略
- **clarify_refactor_scope**: 循环依赖清单；耦合面；模块拆分
- **clarify_problem_details**: 问题细节补全；现象具体化；用户视角复述
- **clarify_problem_scope**: 问题范围界定；改动范围收敛；需求切面
- **clarify_priority_order**: 优先级排序；先查数据还是先查代码；处理顺序确认
- **clarify_context**: 上下文补充；场景背景补齐；业务语境
