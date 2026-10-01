---
name: pax-diagnose
description: >
  对 bug、故障、性能退化、回归进行根因诊断。此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。当用户报告异常、报错或性能下降时，应选择 pax-orchestrate。
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-diagnose

## Execution Contract
- 前置门禁：`snapshot.symptom` 已记录，且 `orchestration.diagnose_required == true`
- 未通过门禁：拒绝启动，返回用户补齐症状描述
- 版本检查：`pax-ops/versions.json`
- 跳过留痕：任何跳过必须记录 `skip_reason`（跳过留痕契约）
- 禁止在 D5 之前输出 `root_cause`
- 禁止在根因假设未验证前输出 `root_cause`
- `severity: P0` 时禁止进入规划阶段，必须升级 `pax-council`
- 所有 RC 未确认时 status 保持 `pending`，不进入下一阶段
- 禁止修改代码或执行修复

## 职责边界
- 做什么：对 bug、故障、性能退化、回归进行根因诊断，产出诊断报告与回归范围
- 不做什么：不修改代码、不执行修复、不做任务规划

## 输入
- 必需：`snapshot.symptom`
- 可选：日志、变更记录、指标、依赖版本

## 工作流

D1→D6 强制顺序，任何跳过必须记录 `skip_reason`。

### D1 复现（Reproduce）

**目标**：确认问题可复现，建立最小复现案例。

**步骤**：
1. 阅读 `symptom.description`，理解问题表现
2. 尝试复现：
   - 使用 `symptom.reproduction` 中的步骤
   - 若无复现步骤，从 `symptom.first_observed` 和 `symptom.recent_changes` 推断
   - 记录实际操作步骤和观察结果
3. 提取错误签名：
   - 错误码 / 异常类型 / 堆栈关键行
   - 时间戳 / 频率 / 间歇性特征
4. 记录环境信息：
   - 运行环境（开发 / 测试 / 生产）
   - 关键版本（代码版本 / 依赖版本 / 配置版本）

**输出**：
```yaml
reproduction:
  status: reproduced | not_reproduced | partial
  method: "<具体操作步骤>"
  observed: "<实际观察到的现象>"
  error_signature: "<错误码 / 异常类型 / 关键特征>"
  environment: "<环境标识 + 关键版本>"
  attempts: <尝试次数>
  first_success_attempt: <第几次成功复现>
```

**失败处理**：
- `not_reproduced` → 标记 `status: blocked`，附 `missing_information`
- `partial` → 记录部分复现结果，继续 D2，但标注不确定性

### D2 证据收集（Evidence Collection）

**目标**：收集支持或反驳假设的证据。

**证据类型**：

| 类型 | 标识 | 来源 | 示例 |
|------|------|------|------|
| 日志 | `log` | 应用日志 / 系统日志 | 错误日志行、WARN 级别记录 |
| 堆栈 | `stack_trace` | 异常堆栈 | NullPointerException 调用链 |
| 变更 | `change` | git log / PR / commit | 最近的相关代码变更 |
| 指标 | `metric` | 监控面板 / APM | 响应时间、错误率、吞吐量 |
| 配置 | `config` | 配置文件 / 环境变量 | 配置项变更 |
| 依赖 | `dependency` | 版本文件 / lock 文件 | 依赖版本变更 |

**收集规则**：
1. 优先收集 `change` 类型（最近变更最可能是根因）
2. 至少收集 3 种不同类型的证据
3. 每条证据标注 `relevance: high | medium | low`
4. 时间戳必须与问题时间窗口重叠

**存储后端确认**（当根因可能涉及数据订正时强制）：
- 确认目标模块的实际存储引擎（MongoDB / MySQL / PostgreSQL / 其他）
- 确认 ORM / DAO 层（JPA / MyBatis / MongoPlus / 原生）
- 确认迁移工具链（Flyway / Liquibase / mongosh / sqlupgrade / 其他）
- 输出：`infrastructure.{storage_backend, orm, migration_tool, script_language}`
- 禁止在未确认存储后端的情况下推测数据订正方式

**输出**：
```yaml
evidence:
  - id: E1
    type: log | stack_trace | change | metric | config | dependency
    source: "<来源路径或系统>"
    timestamp: "<证据时间>"
    content: "<证据摘要>"
    relevance: high | medium | low
  - id: E2
    ...
infrastructure:  # 仅数据相关任务
  storage_backend: MongoDB | MySQL | PostgreSQL | other
  orm: JPA | MyBatis | MongoPlus | native
  migration_tool: Flyway | Liquibase | mongosh | other
  script_language: mongosh | sql | python
```

### D2.5 历史诊断检索（自动执行）

**目标**：检索历史相似诊断，避免重复劳动。

**检索源**：
- `pax-docs` 维护的故障档案
- 历史 snapshot（`diagnosis.root_cause`）
- Issue / PR 记录

**相似度计算**：

| 相似度 | 条件 | 处理 |
|--------|------|------|
| `high` | 同一模块 + 相同错误签名 + 相似时间窗口 | D3 必须优先验证历史根因 |
| `medium` | 同一模块或相似症状 | 作为参考，不强制验证 |
| `low` | 仅症状描述相似 | 记录但不影响 D3 |

**输出**：
```yaml
historical_diagnoses:
  - ref: "<历史诊断 ID 或 ADR 编号>"
    date: "<历史时间>"
    symptom: "<历史症状>"
    root_cause: "<历史根因>"
    similarity: high | medium | low
    relevance_note: "<本次与历史的异同>"
```

### D3 假设生成（Hypothesis Generation）

**目标**：基于证据生成可证伪的假设。

**生成规则**：
1. 每条假设必须可证伪（有明确的验证方法）
2. 每条假设必须关联至少一条证据
3. 生成 2-5 条假设（太少则证据不足，太多则验证成本高）
4. 历史根因 `similarity: high` 时，历史根因必须作为首要假设

**假设结构**：
```yaml
hypotheses:
  - id: H1
    statement: "<可证伪的假设陈述>"
    supporting_evidence: [E1, E3]
    contradicting_evidence: [E2]
    test_method: "<如何验证>"
    status: pending | confirmed | rejected | inconclusive
    confidence: high | medium | low
```

**示例**：
```yaml
hypotheses:
  - id: H1
    statement: "CMDB 字段校验逻辑未区分时间类型，导致对时间字段执行了正则表达式校验"
    supporting_evidence: [E1, E3]
    contradicting_evidence: []
    test_method: "检查校验代码，确认字段类型判断逻辑"
    status: pending
    confidence: high
  - id: H2
    statement: "最近部署的配置变更修改了字段校验规则"
    supporting_evidence: [E2]
    contradicting_evidence: [E4]
    test_method: "对比部署前后的配置变更"
    status: pending
    confidence: medium
```

### D4 假设验证（Hypothesis Validation）

**目标**：验证或反驳每条假设。

**验证方法**：

| 假设类型 | 验证方法 | 工具 |
|----------|----------|------|
| 代码逻辑 | 阅读代码 / 单元测试 | 代码阅读、单元测试 |
| 配置变更 | 对比配置 / git diff | git diff、配置对比 |
| 依赖变更 | 对比版本 / 回滚测试 | 版本对比、回滚测试 |
| 数据问题 | 查询数据 / 检查数据格式 | SQL / Mongo 查询 |
| 性能问题 | 性能测试 / 指标分析 | APM、压测工具 |

**验证结果**：

| 状态 | 语义 | 后续 |
|------|------|------|
| `confirmed` | 验证成功，假设成立 | 进入 D5 |
| `rejected` | 验证失败，假设不成立 | 继续验证下一条 |
| `inconclusive` | 证据不足，无法判定 | 标记风险，继续 |

**输出**：
```yaml
hypotheses:
  - id: H1
    status: confirmed
    test_performed: "<实际执行的验证动作>"
    result: "<验证结果>"
    evidence: [E5, E6]  # 新增的验证证据
    confidence: high
```

### D5 根因收敛（Root Cause Convergence）

**目标**：收敛到唯一根因，评估严重度。

**收敛规则**：
1. 所有假设必须已验证（`confirmed` / `rejected` / `inconclusive`）
2. 至少一条假设必须 `confirmed`
3. 若有多个 `confirmed`，合并为组合根因
4. 禁止用"可能""大概""疑似"填充证据缺口

**根因结构**：
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
  contributing_factors:
    - "<促成因素>"
  regression_scope:
    - module: "<模块名>"
      reason: "<为什么受影响>"
      priority: must_test | should_test | nice_to_test
      source: domain_map | inferred
```

**严重度量化标准**（`references/severity-criteria.md`）：

| 等级 | 判断标准 | 触发 |
|------|----------|------|
| **P0** | 核心流程完全不可用 / 影响所有用户 / 无规避 / 安全相关 | 强制升级 `pax-council` |
| **P1** | 核心流程部分不可用 / 影响部分用户 / 有临时规避 | 走 `plan → execute → review` |
| **P2** | 非核心流程部分不可用 / 影响少量用户 / 有明显规避 | 可合并到常规迭代 |

### D6 报告产出（Report）

**目标**：产出结构化诊断报告。

**报告结构**：
```markdown
# 诊断报告

## 1. 症状摘要
- 问题描述：...
- 影响范围：...
- 首次发现：...

## 2. 复现结果
- 状态：reproduced / not_reproduced / partial
- 方法：...
- 观察：...

## 3. 证据清单
| ID | 类型 | 来源 | 相关性 | 摘要 |
|----|------|------|--------|------|
| E1 | log  | ...  | high   | ...  |

## 4. 假设验证
| ID | 假设 | 状态 | 置信度 | 验证方法 |
|----|------|------|--------|----------|
| H1 | ...  | confirmed | high | ... |

## 5. 根因分析
- 根因：...
- 置信度：...
- 严重度：...
- 促成因素：...

## 6. 回归范围
| 模块 | 原因 | 优先级 |
|------|------|--------|
| ...  | ...  | must_test |

## 7. 最小复现
...

## 8. 建议
...
```

**Review Checklist（RC1-RC7）**：

| RC | 检查项 | 通过标准 |
|----|--------|----------|
| RC1 | 问题可复现 | `reproduction.status == reproduced` |
| RC2 | 根因有证据支持 | `root_cause.confidence >= medium` |
| RC3 | 假设已验证 | 所有假设 `status != pending` |
| RC4 | 严重度已评估 | `severity_rationale` 完整 |
| RC5 | 回归范围已确定 | `regression_scope` 非空 |
| RC6 | 无证据缺口 | 无"可能""大概""疑似" |
| RC7 | 存储后端已确认（数据任务） | `infrastructure` 完整 |

**信息不足声明机制**：
任何一步证据不足时输出 `status: blocked`，附 `blocked_at` 与 `missing_information`；禁止用"可能""大概""疑似"填充证据缺口。

**RC 拒绝回退映射**：

| RC | 回退到 |
|----|--------|
| RC1 | D1 |
| RC2 / RC6 | D3 / D4 |
| RC3 / RC4 / RC5 | D5 |
| RC7 | D2 |

## 输出契约
- `snapshot.diagnosis`（含 `reproduction` / `evidence` / `hypotheses` / `root_cause` / `review_checklist`）
- `diagnosis_report.md`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 证据不足 → `status: blocked`，附 `blocked_at` 与 `missing_information`
- `severity: P0` → 禁止进入规划阶段，升级 `pax-council`
- RC 检查失败 → 按上表回退到对应步骤
- 跳过任何 D 步骤 → 必须记录 `skip_reason`

## 何时升级
- `severity: P0` 或涉及架构级根因 → `pax-council`
- 需要历史档案检索 → `pax-docs`
- 需要独立复现 → `pax-worker-*`
- 需要独立评审 → `pax-review`
