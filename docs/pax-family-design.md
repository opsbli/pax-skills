# pax-* 家族 Skill 详细设计需求文档

**版本**：1.0.0
**状态**：设计稿
**家族名**：pax
**展开**：Pact-based Agreement eXecution
**定位**：以软件工程方法构建的可组合、可审计、可版本化的 AI Skill 家族

---

## 1. 背景与目标

### 1.1 背景

当前 AI Agent 的 Skill 生态存在以下问题：

- **流程驱动而非状态驱动**：Skill 依赖对话节奏推进，缺乏显式状态，无法判断"何时该问、问多少、何时停"。
- **缺乏契约**：Skill 之间通过自然语言传递状态，信息丢失、意图漂移。
- **不可审计**：诊断、决策、跳过、失败缺乏结构化留痕。
- **难以扩展**：新增 Skill 靠手工定制，家族契约靠自觉维护。
- **缺乏版本治理**：多 Skill 协作时无兼容矩阵，breaking change 无迁移路径。

### 1.2 目标

构建 `pax-*` 家族，使 AI 能力成为：

- **可组合**：Skill 之间通过结构化快照通信，可动态编排。
- **可审计**：每个阶段的状态、决策、跳过、失败全部留痕。
- **可验证**：契约测试强制家族规则，不靠 AI 自觉。
- **可版本化**：家族统一版本线，兼容矩阵显式管理。
- **可演化**：通过 `pax-forge` 工程化扩展，通过 `pax-evolve` 自我优化。

### 1.3 非目标

- 不追求通用 Agent 框架。
- 不绑定具体模型或运行时。
- 不替代领域专业知识。
- 不追求"一次设计永久适用"——家族设计本身是可演化的制品。

---

## 2. 设计原则

### 2.1 核心原则

| 原则 | 说明 |
|---|---|
| **快照即契约** | 所有跨 Skill 状态通过结构化快照传递，不用自然语言。 |
| **状态机驱动** | 每个 Skill 在共识状态机上有明确位置，行为由状态缺口决定。 |
| **风险定精度** | 风险等级决定需要确认到多细，不决定问几个问题。 |
| **关注点分离** | 澄清、诊断、规划、执行、评审互不混叠。 |
| **前置门禁** | 每个 Skill 的 Execution Contract 定义前置条件，不满足不启动。 |
| **跳过留痕** | 任何跳过必须有 `skip_reason`，且可被审计。 |
| **增量沉淀** | 文档只写已确认硬决策，待定项留在草稿区。 |
| **保留上游同步** | 借鉴外部 Skill 时保留 `upstream` 映射，避免彻底分叉。 |

### 2.2 从 tri-stack 借鉴的经验

- MECE 路由 + 快照交接
- Execution Contract 作为 Skill 宪法
- 声明式补丁层 + 幂等重放
- 横向方法论层不进路由
- 渐进式交付 + 阶段门禁

### 2.3 从 grill-me-with-doc 借鉴的经验

- 一次一问与按轮次批量提问并存
- 设计树（Design Tree）+ 前沿（Frontier）计算
- 实时文档沉淀（CONTEXT.md / ADR）
- 自主获取环境事实，不询问用户

---

## 3. 家族契约

任何 `pax-*` 成员必须遵守以下五条契约，否则不允许进入家族。

### 3.1 命名契约

- 格式：`pax-<capability>`
- 能力即接口，名字必须让路由层和用户判断生命周期位置
- 元层工具使用 `pax-forge`，不占用 L0–L4 命名空间

### 3.2 快照契约

- 所有跨 Skill 状态通过 `pax-snapshot.yaml` 传递
- 快照是唯一交接真相源
- 快照结构由 `pax-family.schema.yaml` 约束
- 下游 Skill 直接读快照，不重新识别意图

### 3.3 状态契约

- 每个 Skill 必须声明其在共识状态机中的位置
- 不允许一个 Skill 同时承担两个阶段
- 状态机维度：`unknown → fuzzy → assumption → confirmed → locked`

### 3.4 前置契约

- 每个 SKILL.md 开头必须有 Execution Contract
- 声明前置门禁、版本检查、失败处理
- 门禁不通过，主流程不启动

### 3.5 版本契约

- 家族统一版本线，单个 Skill 独立补丁版本
- 任何 breaking change 必须升 major，并更新兼容矩阵
- 版本来源单一：`pax-ops/versions.json`
- Skill frontmatter 的 version 由 `pax-forge` 注入，不手工维护

---

## 4. 分层架构

### 4.1 层级总览

```text
元层   pax-forge        ← 开发/维护工具，不参与运行时

L0     pax-orchestrate  ← 路由、风险分级、生命周期

L1     pax-clarify      ← 共识状态机（必经）
       pax-diagnose     ← 根因诊断（可选）
       pax-plan         ← 结构化规划（必经）
       pax-execute      ← 契约约束下执行（必经）
       pax-review       ← 独立评审门禁（必经）

L2     pax-advisor      ← 单点咨询（按需）
       pax-council      ← 多专家盲审（高风险）

L3     pax-worker-*     ← 工具适配层（可替换）

L4     pax-verify       ← 运行中验证（横切）
       pax-evolve       ← 自进化（横切）
       pax-docs         ← 文档沉淀（横切）
```

### 4.2 各层职责边界

| 层 | 职责 | 不做什么 |
|---|---|---|
| 元层 | 生成、校验、注册、版本管理 | 不参与运行时 |
| L0 | 路由、风险分级、生命周期 | 不执行具体工作 |
| L1 | 生命周期阶段推进 | 不跨阶段、不越权 |
| L2 | 特定问题咨询、高风险决策 | 不改变主流程 |
| L3 | 与具体模型/运行时绑定 | 接口由上层定义 |
| L4 | 质量保障、自进化、文档 | 不认领路由落点 |

---

## 5. 核心数据模型

### 5.1 `pax-snapshot.yaml` 结构

```yaml
meta:
  version: 1.0
  created_at: "<ISO8601>"
  updated_at: "<ISO8601>"
  skill_lineage: [pax-orchestrate, pax-clarify, ...]

goal:
  statement: "<用户目标>"
  success_criteria: [...]

consensus:
  required_precision: low | medium | high
  dimensions:
    goal: unknown | fuzzy | assumption | confirmed | locked
    success_criteria: ...
    constraints: ...
    authorization: ...
    exceptions: ...
    terminology: ...
  design_tree:
    - id: D<N>
      question: "<待决策问题>"
      status: settled | frontier | blocked | skipped
      answer: "<已确定答案>"
      depends_on: [D<M>]
      children: [D<K>]
      skip_reason: null
  gaps_remaining: [...]

orchestration:
  diagnose_required: true | false
  rationale: "<决策理由>"
  skip_reason: null
  route: [pax-clarify, pax-diagnose, pax-plan, pax-execute, pax-review]
  question_strategy: batch | one-by-one

symptom:                                # 仅诊断类任务
  description: "..."
  impact: "..."
  reproduction: "..."
  first_observed: "<ISO8601>"
  recent_changes: [...]

diagnosis:                              # 仅诊断类任务
  status: settled | blocked | escalated | pending
  step_audit:
    - { step: D<N>, status: settled|skipped, skip_reason: null }
  reproduction:
    status: reproduced | not_reproduced | partial
    method: "..."
    observed: "..."
    error_signature: "..."
    environment: "..."
  evidence:
    - { type: ..., source: ..., timestamp: ..., content: ..., relevance: ... }
  historical_diagnoses:
    - { ref: ..., date: ..., symptom: ..., root_cause: ..., similarity: ..., relevance_note: ... }
  hypotheses:
    - { id: H<N>, statement: ..., status: pending|confirmed|rejected|inconclusive, test_performed: ..., result: ..., evidence: [...] }
  root_cause:
    statement: "..."
    confidence: high | medium | low
    confidence_rationale: "..."
    severity: P0 | P1 | P2
    severity_rationale:
      core_flow_broken: true | false
      affected_users: all | most | some | few
      workaround_available: true | false
      security_relevant: true | false
    minimal_repro: "..."
    contributing_factors: [...]
    regression_scope:
      - { module: ..., reason: ..., priority: must_test|should_test|nice_to_test, source: domain_map|inferred }
  blocked_history:
    - { step: ..., blocked_at: ..., missing_information: [...], suggested_sources: [...], resolved_at: ..., resolution: ... }
  review_checklist:
    - { id: RC<N>, item: ..., result: ..., confirmed: true | false }
  diagnosed_at: "<ISO8601>"

plan:
  steps: [...]
  dependencies: [...]
  evidence: [...]
  verification_strategy: [...]
  status: draft | frozen

contract:
  authorization: {...}
  constraints: [...]
  exceptions: [...]
  assumptions: [...]
  withdraw: [...]

execution:
  mode: normal | fix
  log: [...]
  deviations: [...]
  changes: [...]

review:
  verdict: pass | fail | partial | blocked | escalated
  stamp: "..."
  rationale: "..."

quality:
  verification_seals: [...]
  evolution_entries: [...]
```

### 5.2 快照不变式

- `skill_lineage` 必须按执行顺序记录
- 任何 `status: settled` 的维度必须有对应证据
- `diagnosis.root_cause` 只能在 D5 settled 后出现
- `contract` 必须在 `pax-execute` 前生成并经用户确认
- `review.verdict` 必须附带 `rationale`

---

## 6. Skill 详细设计

### 6.1 `pax-orchestrate`（L0）

**职责**：路由、风险分级、生命周期管理、快照初始化。

**输入**：用户目标、现有上下文。

**输出**：路由决策、风险等级、`question_strategy`、快照初始化。

**核心逻辑**：

```python
def orchestrate(user_goal, context):
    intent = classify_intent(user_goal)         # MECE 分类
    risk = assess_risk(user_goal, context)      # 四维评分
    diagnose_required = is_diagnostic_intent(intent, context)
    strategy = "batch" if risk <= 9 else "one-by-one"
    route = build_route(intent, diagnose_required, risk)
    return init_snapshot(intent, risk, diagnose_required, strategy, route)
```

**风险评分维度**（每项 1–3 分）：

- 不可逆性
- 影响范围
- 不确定性
- 协调成本

**总分映射**：

- **4–6**：低风险，`required_precision: low`
- **7–9**：中风险，`required_precision: medium`
- **10–12**：高风险，`required_precision: high`

**路由规则**：

```text
诊断类意图（修复 / 报错 / 异常 / 回归 / 性能退化）
  → [clarify, diagnose, plan, execute, review]

普通任务
  → [clarify, plan, execute, review]
```

**跳过诊断的条件**（必须显式记录）：

- 新建功能，无既有行为
- 根因已在 clarify 阶段完全确定且用户确认
- 纯文档、纯咨询、纯规划类任务
- 用户明确要求"先别查根因，直接改"

**Execution Contract**：

- 前置：能读取 `pax-family.schema.yaml`
- 风险评分必须记录四维分数和总分
- `diagnose_required` 决策必须附 `rationale` 或 `skip_reason`
- 路由必须符合 MECE 原则

### 6.2 `pax-clarify`（L1，必经）

**职责**：共识状态机、设计树维护、缺口检测、契约草稿。

**输入**：`pax-orchestrate` 的快照、`question_strategy`。

**输出**：更新 `consensus`、`contract` 草稿、`gaps_remaining`。

**双引擎驱动**：

- **设计树引擎**：负责逻辑完备性
  - 将目标分解为可判定的决策节点
  - 标注依赖关系（`depends_on` / `children`）
  - 计算前沿（Frontier）：所有 `depends_on` 均已 settled 的节点
  - 用户回答后重塑设计树，解锁后续问题
- **共识维度引擎**：负责风险适配精度
  - 检测每个维度的状态是否达到 `required_precision`
  - 结合设计树的逻辑完备性，判断是否收敛

**工作流**：

```text
1. 初始化设计树（从 pax-orchestrate 的路由结果出发）
2. 循环：
   a. 计算前沿（frontier = 所有依赖已 settled 的未决节点）
   b. 若 strategy == batch：
        一次性输出所有前沿问题，附推荐答案
      若 strategy == one-by-one：
        按优先级逐个提问，每次一个
   c. 对需要环境事实的问题，调度 pax-worker-* 自动获取，不询问用户
   d. 记录答案，标记 settled，重塑设计树
   e. 同步更新 consensus.dimensions
   f. 检测剩余缺口
3. 终止条件：
   - frontier 为空
   - 且所有 required_precision 维度达到 confirmed / locked
4. 产出契约草稿，等待用户确认
```

**问题选择原则**：

- 只问能改变行动的问题
- 优先"默认假设 + 风险标注"，而非开放式提问
- 阻塞性缺口必须问；优化性缺口给默认值；可后置缺口写入待办

**失败模式**：

- 用户回答矛盾 → 标记冲突，请求澄清
- 用户疲劳 → 自动降级为 batch 模式，减少轮次
- 无法收敛 → 升级 `pax-council`

**Execution Contract**：

- 前置：快照已初始化，`question_strategy` 已确定
- 禁止在 frontier 非空时进入 `pax-plan`
- 每次提问必须对应设计树节点或共识维度缺口
- 环境事实不得询问用户，必须调度 `pax-worker-*`

### 6.3 `pax-diagnose`（L1，可选）

**职责**：对 bug、故障、性能退化、回归进行根因诊断。

**输入**：`snapshot.symptom`、`orchestration.diagnose_required == true`。

**输出**：`snapshot.diagnosis`、`diagnosis_report.md`。

**六步工作流**（强制顺序，跳过留痕）：

#### D1 复现（Reproduce）

```yaml
reproduction:
  status: reproduced | not_reproduced | partial
  method: "<具体命令或操作>"
  observed: "<实际观察到的现象>"
  error_signature: "<错误码或异常类型>"
  environment: "<环境标识>"
```

#### D2 证据收集（Evidence Collection）

```yaml
evidence:
  - type: log | stack_trace | change | metric | config | dependency
    source: "<具体来源路径或系统>"
    timestamp: "<证据时间>"
    content: "<摘要>"
    relevance: high | medium | low

historical_diagnoses:                   # 自动检索，见 D2.5
  - ref: "<历史诊断 ID 或 ADR 编号>"
    date: "<历史时间>"
    symptom: "<历史症状>"
    root_cause: "<历史根因>"
    similarity: high | medium | low
    relevance_note: "<本次与历史的异同>"
```

#### D2.5 历史诊断检索（自动执行）

- **检索源**：`pax-docs` 维护的故障档案、历史 snapshot、issue/PR
- `similarity: high` 时，D3 假设生成必须优先验证历史根因

#### D3 假设生成（Hypothesis Generation）

```yaml
hypotheses:
  - id: H<N>
    statement: "<可证伪的假设陈述>"
    supporting_evidence: [evidence_id]
    contradicting_evidence: [evidence_id]
    test_method: "<如何验证>"
    status: pending
```

#### D4 假设验证（Hypothesis Validation）

```yaml
hypotheses:
  - id: H<N>
    status: confirmed | rejected | inconclusive
    test_performed: "<实际验证动作>"
    result: "<结果>"
    evidence: [evidence_id]
```

#### D5 根因收敛（Root Cause Convergence）

```yaml
root_cause:
  statement: "<根因陈述>"
  confidence: high | medium | low
  confidence_rationale: "<为何是这个置信度>"
  severity: P0 | P1 | P2
  severity_rationale:
    core_flow_broken: true | false
    affected_users: all | most | some | few
    workaround_available: true | false
    security_relevant: true | false
  minimal_repro: "<最小复现步骤或案例>"
  contributing_factors: [...]
  regression_scope:
    - module: "<模块名>"
      reason: "<为什么受影响>"
      priority: must_test | should_test | nice_to_test
      source: domain_map | inferred
```

#### D6 报告产出（Report）

```yaml
diagnosis_report.md: 结构化报告
review_checklist:
  - { id: RC1, item: "症状复现方法可靠", result: "...", confirmed: false }
  - { id: RC2, item: "根因假设经过验证", result: "...", confirmed: false }
  - { id: RC3, item: "最小复现案例可独立触发", result: "...", confirmed: false }
  - { id: RC4, item: "回归范围覆盖 must_test 模块", result: "...", confirmed: false }
  - { id: RC5, item: "严重度评估符合标准", result: "...", confirmed: false }
  - { id: RC6, item: "无未验证假设被当作根因", result: "...", confirmed: false }
  - { id: RC7, item: "历史相似诊断已关联", result: "...", confirmed: false }
```

**信息不足声明机制**：

任何一步证据不足时：

```yaml
status: blocked
blocked_at: D<N>
missing_information: [具体缺什么]
suggested_sources: [从哪里可以获取]
```

- 禁止在 blocked 状态下进入下一步
- 禁止用"可能""大概""疑似"填充证据缺口

**RC 拒绝回退映射**：

| RC | 回退到 |
|---|---|
| RC1 | D1 |
| RC2 / RC6 | D3 / D4 |
| RC3 / RC4 / RC5 | D5 |
| RC7 | D2 |

**风险等级量化标准**（`references/severity-criteria.md`）：

| 等级 | 判断标准 | 触发 |
|---|---|---|
| **P0** | 核心流程完全不可用 / 影响所有用户 / 无规避 / 安全相关 | 强制升级 `pax-council`，人工审批 |
| **P1** | 核心流程部分不可用 / 影响部分用户 / 有临时规避 | 正常走 `plan → execute → review` |
| **P2** | 非核心流程部分不可用 / 影响少量用户 / 有明显规避 | 可合并到常规迭代 |

**Execution Contract**：

- 前置：`snapshot.symptom` 已记录，且 `diagnose_required == true`
- D1→D6 必须按序执行，跳过必须有 `skip_reason`
- 禁止在 D5 之前输出 `root_cause`
- 禁止在根因假设未验证前输出 `root_cause`
- `severity: P0` 时禁止进入 `pax-plan`，必须升级 `pax-council`
- 所有 RC 未确认时 status 保持 `pending`，不进入 `pax-plan`
- 禁止修改代码或执行修复

### 6.4 `pax-plan`（L1，必经）

**职责**：将已澄清/诊断的目标转化为机器可冻结的任务计划。

**输入**：快照的 `consensus` 和 `diagnosis` 区。

**输出**：`plan` 区、`plan_summary.md`。

**前置门禁**：

- `consensus.gaps_remaining == []`
- 诊断类任务：`diagnosis.status == settled` 且 `confidence >= medium`

**工作流**：

1. 读取快照，校验门禁
2. 分解目标为步骤，每步绑定证据
3. 标注依赖、风险、回退点
4. 定义验证策略（`verification_strategy`）
5. 写入快照 `plan` 区，状态置 `frozen`
6. 触发 `pax-review` 或返回用户确认

**输出格式**：

```yaml
plan:
  steps:
    - id: S<N>
      action: "..."
      inputs: [...]
      outputs: [...]
      depends_on: [S<M>]
      rollback: "..."
  dependencies: [...]
  evidence: [...]
  verification_strategy:
    - { step: S<N>, method: "...", criteria: "..." }
  status: frozen
```

**失败模式**：

- 快照缺失 → 降级为独立模式，自行初始化最小快照
- 门禁不通过 → 返回 `pax-clarify` 或 `pax-diagnose`
- 计划无法收敛 → 升级 `pax-council`

### 6.5 `pax-execute`（L1，必经）

**职责**：在契约约束下执行，带审计和回滚。

**输入**：`plan` 区、`contract` 区。

**输出**：`execution` 区。

**执行模式**：

- `mode: normal`：常规执行
- `mode: fix`：修复模式，必须针对已确认根因，必须包含回归测试

**工作流**：

1. 校验契约已确认
2. 按计划步骤执行
3. 每步内环验证：做 → 验 → 修
4. 记录执行日志和变更
5. 检测偏差：若偏离契约，暂停并重新协商
6. 完成后触发 `pax-verify`

**输出格式**：

```yaml
execution:
  mode: normal | fix
  log:
    - { step: S<N>, action: "...", result: "...", timestamp: "..." }
  deviations:
    - { step: S<N>, deviation: "...", action: "..." }
  changes: [...]
```

**fix 模式约束**：

- 修复必须针对已确认根因，不能"顺手改别的"
- 必须包含回归测试
- 必须验证修复不引入新问题
- 修复后重新运行 `pax-diagnose` 的最小复现案例
- 若发现根因判断有误，不允许自行重新诊断，必须返回 `pax-diagnose`

**Execution Contract**：

- 前置：`contract` 已确认，`plan.status == frozen`
- 未通过内环验证不得标记完成
- 偏离契约必须暂停并重新协商
- fix 模式必须包含回归测试

### 6.6 `pax-review`（L1，必经）

**职责**：独立评审门禁，对照成功标准决定通过/拒绝。

**输入**：`execution` 区、`plan` 区、`contract` 区。

**输出**：`review` 区。

**工作流**：

1. 读取执行结果和成功标准
2. 对照标准逐项验收
3. 检查偏差是否已处理
4. 检查 `pax-verify` 印章
5. 产出评审结论和印章

**输出格式**：

```yaml
review:
  verdict: pass | fail | partial | blocked | escalated
  stamp: "<唯一标识>"
  rationale: "..."
  findings: [...]
```

**门禁**：

- `verdict: pass` 才能进入 `pax-docs`
- `verdict: fail` 返回 `pax-execute`
- `verdict: escalated` 升级 `pax-council`

### 6.7 `pax-advisor`（L2）

**职责**：只读顾问，针对特定假设、权衡、架构问题提供咨询。

**输入**：具体的咨询问题。

**输出**：咨询意见（不修改快照）。

**约束**：

- 只读，不修改快照
- 不改变主流程
- 不认领路由落点

### 6.8 `pax-council`（L2）

**职责**：对重大系统开发计划做盲审、显式反驳、有界修订轮次、证据加权决策。

**触发条件**：

- 高风险任务（`required_precision: high`）
- `diagnosis.severity: P0`
- 根因涉及架构级问题
- 疑似安全漏洞
- `pax-review` 标记 `escalated`

**输入**：完整快照。

**输出**：证据加权决策、异议记录。

**约束**：

- 不改变主流程，只提供决策
- 决策必须附带证据和异议记录

### 6.9 `pax-worker-*`（L3）

**职责**：将有界实现任务委托给固定 worker，在沙箱和无头执行下运行。

**示例**：

- `pax-worker-grok`：Grok 有界任务执行
- `pax-worker-codex`：Codex 有界任务执行

**约束**：

- 接口由 L1 定义，实现可替换
- 上层不关心底层是哪个模型
- 必须有沙箱和无头执行约束

### 6.10 `pax-verify`（L4，横切）

**职责**：运行中验证，有界循环 + 五态印章。

**输入**：执行结果。

**输出**：验证印章。

**五态**：`pass`、`fail`、`partial`、`blocked`、`escalated`

**约束**：

- 不认领路由落点
- 可被任何 L1/L2 Skill 调用
- 验证必须独立、可审计

### 6.11 `pax-evolve`（L4，横切）

**职责**：OODA 闭环 + 经验条目库 + A/B 验证门 + 回滚。

**输入**：执行反馈、失败案例。

**输出**：经验条目、A/B 验证结果、回滚决策。

**约束**：

- 不认领路由落点
- 变更必须经过 A/B 验证门
- 支持回滚

### 6.12 `pax-docs`（L4，横切）

**职责**：把已确认硬决策沉淀为 `CONTEXT.md` 和 ADR。

**输入**：快照中已确认的硬决策。

**输出**：`CONTEXT.md`、ADR 文件。

**约束**：

- 不认领路由落点
- 增量写入，不污染正式文档
- 草稿区与正式区分离
- 最后统一审核后合并

### 6.13 `pax-forge`（元层）

**职责**：按家族契约生成、校验、注册新 Skill。

**输入**：新 Skill 名称、层、职责描述。

**输出**：骨架目录、契约测试、注册记录、待办清单。

**工作流**：

```text
1. 读取 pax-family.schema.yaml
2. 命名冲突与层合法性检查
3. 选择模板（按层选择不同骨架）
4. 生成目录结构与 SKILL.md
5. 生成契约测试
6. 注册到 pax-ops/registry.json
7. 运行契约测试
8. 输出待办清单
```

**核心机制**：

- **契约即 Schema**：生成和校验共用 `pax-family.schema.yaml`
- **Schema 是唯一真相源**：改 Schema 等于改家族宪法
- **生成即校验**：生成的契约测试立即运行

**模板系统**（按层选择）：

| 层 | 模板特征 |
|---|---|
| L1 | 强制包含快照读写、前置门禁、失败降级路径 |
| L2 | 只读，不修改快照，输出咨询意见 |
| L3 | 绑定具体模型/运行时，接口由上层定义 |
| L4 | 不认领路由落点，可被任何层调用 |

**契约测试至少校验**：

- frontmatter 完整性
- snapshot schema 兼容性
- 层间调用合法性
- 版本契约
- 无循环依赖
- 跳过审计（针对可选 Skill）
- 门禁行为

**弃用流程**：

```text
1. 标记 status: deprecated
2. 生成迁移指南
3. 更新兼容矩阵
4. 保留一个 minor 版本的过渡期
5. 检查所有调用方，输出受影响清单
6. 过渡期后标记 status: removed
```

**Execution Contract**：

- 前置：必须能读取 `pax-family.schema.yaml`
- 生成前必须做命名冲突检查
- 生成后必须运行契约测试，未通过不注册
- 不修改已有 Skill 的业务逻辑
- breaking change 必须人工审核

---

## 7. 版本与治理

### 7.1 版本来源单一

`pax-ops/versions.json` 是唯一版本基线：

```json
{
  "family": "pax",
  "version": "1.0",
  "skills": {
    "pax-clarify":  { "layer": "L1", "version": "1.0.0", "status": "active" },
    "pax-diagnose": { "layer": "L1", "optional": true, "version": "1.0.0", "status": "active" },
    "pax-plan":     { "layer": "L1", "version": "1.0.0", "status": "active" },
    "pax-execute":  { "layer": "L1", "version": "1.0.0", "status": "active" },
    "pax-review":   { "layer": "L1", "version": "1.0.0", "status": "active" }
  },
  "compatibility_matrix": {
    "pax-clarify@1":  ["pax-diagnose@1", "pax-plan@1"],
    "pax-diagnose@1": ["pax-plan@1"],
    "pax-plan@1":     ["pax-execute@1"],
    "pax-execute@1":  ["pax-review@1"]
  }
}
```

Skill frontmatter 的 `version` 由 `pax-forge` 注入，不手工维护。

### 7.2 契约测试

任何 `pax-*` 变更后，自动跑跨 Skill 契约测试：

- 快照 Schema 校验
- I/O 兼容性
- 门禁行为
- 版本契约
- 无循环依赖
- 跳过审计

### 7.3 补丁层

`pax-ops/patches/manifest.json` 作为唯一变更入口，`apply.py` 幂等重放。**禁止直接修改 Skill 本体。**

### 7.4 弃用流程

1. 旧 Skill 标记 `deprecated`
2. 给迁移窗口（一个 minor 版本）
3. 不直接删除，避免破坏调用方
4. 过渡期后标记 `removed`

### 7.5 保留上游同步

- 借鉴外部 Skill 时保留 `upstream:` 字段
- 优先用补丁层覆盖差异，而非复制整个文件
- 保留同步脚本，避免彻底分叉

---

## 8. 评估与迭代

### 8.1 Skill Lift 评估

A/B 测试每个 Skill 的贡献：

- 启用该 Skill 与禁用时的得分差值
- 家族内部做组合测试（如 `pax-plan + pax-execute` 的联合 Lift）
- 参考 NVIDIA SkillEvaluator 方法：300+ Verified Skills 平均提升 31 分

### 8.2 评估指标

| 指标 | 说明 |
|---|---|
| **返工率** | 执行后因需求错位返工的比例 |
| **共识达成时间** | 从开始到契约确认的耗时 |
| **问题有效性** | 每个问题是否改变了方案或消除了阻塞 |
| **过度提问率** | 问了但不影响行动的问题占比 |
| **Skill Lift** | 启用该 Skill 前后任务成功率提升 |
| **用户认知负荷** | 用户是否感到疲劳轰炸 |

### 8.3 自进化

`pax-evolve` 实现 OODA 闭环：

- **Observe**：收集执行反馈、失败案例
- **Orient**：分析失败原因，定位底层缺陷
- **Decide**：决定优化方向
- **Act**：重写 Skill 定义，经 A/B 验证后发布
- **回滚**：若验证不通过，回滚到上一版本

参考 SkillForge 框架：`Failure Analyzer → Skill Diagnostic → Skill Optimizer` 循环迭代。

---

## 9. 最小可运行家族清单

| Skill | 层 | 可选 | 职责 | 关键输出 |
|---|---|---|---|---|
| `pax-forge`       | 元 | 否 | 生成、校验、注册 | 骨架 + 契约测试 |
| `pax-orchestrate` | L0 | 否 | 路由、风险分级   | 路由决策 + 快照 |
| `pax-clarify`     | L1 | 否 | 共识状态机       | 共识状态 + 契约草稿 |
| `pax-diagnose`    | L1 | 是 | 根因诊断         | `diagnosis` 区 |
| `pax-plan`        | L1 | 否 | 结构化规划       | `plan` 区 |
| `pax-execute`     | L1 | 否 | 契约约束下执行   | `execution` 区 |
| `pax-review`      | L1 | 否 | 独立评审门禁     | `review` 区 |
| `pax-advisor`     | L2 | 是 | 单点咨询         | 咨询意见 |
| `pax-council`     | L2 | 是 | 多专家盲审       | 决策 + 异议 |
| `pax-worker-*`    | L3 | 是 | 有界任务执行     | 变更 |
| `pax-verify`      | L4 | 是 | 运行中验证       | 五态印章 |
| `pax-evolve`      | L4 | 是 | 自进化           | 经验条目 |
| `pax-docs`        | L4 | 是 | 文档沉淀         | `CONTEXT.md` / ADR |

---

## 10. 附录

### 10.1 `SKILL.md` 标准骨架

```markdown
---
name: pax-<capability>
description: >
  <能力描述>。当 <使用场景> 时使用。
version: <由 pax-forge 注入>
family: pax
layer: <L0|L1|L2|L3|L4|meta>
optional: <true|false>
requires_snapshot: <true|false>
upstream: <可选，外部来源映射>
---

# pax-<capability>

## Execution Contract
- 前置门禁：...
- 未通过门禁：...
- 版本检查：...

## 职责边界
- 做什么：...
- 不做什么：...

## 输入
- 必需：...
- 可选：...

## 工作流
1. ...
2. ...

## 输出契约
- <文件或数据结构>，格式由 <Schema 引用> 约束

## 失败模式
- 如果 <条件>，则 <行为>

## 何时升级
- 如果 <风险触发条件>，调用 <Skill>
```

### 10.2 `pax-family.schema.yaml` 骨架

```yaml
family: pax
family_expansion: "Pact-based Agreement eXecution"
version: 1.0
layers:
  meta: [forge]
  L0: [orchestrate]
  L1: [clarify, diagnose, plan, execute, review]
  L2: [advisor, council]
  L3: ["worker-*"]
  L4: [verify, evolve, docs]
contracts:
  naming: "^pax-[a-z][a-z0-9-]*$"
  required_frontmatter:
    - name
    - description
    - version
    - family
    - layer
    - requires_snapshot
  required_sections:
    - Execution Contract
    - 职责边界
    - 输入
    - 工作流
    - 输出契约
    - 失败模式
    - 何时升级
  snapshot_schema: "./schemas/snapshot.schema.json"
  version_source: "./pax-ops/versions.json"
```

### 10.3 领域依赖映射表示例

```markdown
# 领域依赖映射表

## 认证/授权
- 根因：密钥轮换、token 失效、权限模型变更
- 必测：登录、注册、token 刷新、权限校验、SSO
- 应测：用户信息接口、审计日志

## 支付
- 根因：支付网关变更、订单状态机变更
- 必测：下单、支付回调、订单状态、退款
- 应测：订单列表、支付记录、对账

## 数据一致性
- 根因：事务边界、并发控制、缓存失效
- 必测：写后读、并发写、缓存穿透
- 应测：报表、导出、异步任务
```

---

> **说明**：本设计文档定义了 `pax-*` 家族的完整契约、分层架构、核心数据模型、每个 Skill 的详细设计、版本治理、评估与迭代机制。所有设计遵循"快照即契约、状态机驱动、风险定精度、关注点分离、前置门禁、跳过留痕"的核心原则，目标是构建一个可组合、可审计、可验证、可版本化、可演化的 AI Skill 家族。
