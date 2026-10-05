# pax-* 使用示例

本文档提供 pax-* 家族的完整使用示例，帮助快速上手。

## 示例 1: CMDB 数据订正（data_ops 场景）

### 场景描述

数据库中的时间格式不一致，需要批量订正为 ISO 8601 格式。

### 用户输入

```
数据库中的时间格式不一致，需要批量订正
```

### 执行流程

```
pax-orchestrate → pax-clarify → pax-diagnose → pax-plan → pax-execute → pax-review
```

### 详细步骤

#### 1. pax-orchestrate: 意图分类与路由构建

**意图分类**:
- 一级意图: `data_ops`
- 二级意图: `data_integrity`

**风险评分**:
| 维度 | 分数 | 说明 |
|------|------|------|
| 不可逆性 | 2 | 数据修改可以回滚但需要备份 |
| 影响范围 | 3 | 影响所有用户数据 |
| 不确定性 | 2 | 需要确认订正规则 |
| 协调成本 | 1 | 单模块操作 |
| **总分** | **8** | **medium** |

**路由**: `[clarify, diagnose, plan, execute, review]`

**快照初始化**:
```yaml
meta:
  version: 1.0
  created_at: "2026-10-01T15:33:00+08:00"
  skill_lineage: ["pax-orchestrate"]

orchestration:
  intent:
    primary: data_ops
    secondary: data_integrity
    classification_rationale: "用户输入包含'订正'、'批量'等数据操作信号"
  risk:
    total: 8
    level: medium
  diagnose_required: true
  route: [clarify, diagnose, plan, execute, review]
```

#### 2. pax-clarify: 需求澄清

**设计树**:
```yaml
design_tree:
  - id: D1
    question: "数据问题的具体表现？"
    status: settled
    answer: "时间格式不一致（ISO 8601、空格分隔、UTC）"
  
  - id: D2
    question: "数据规模和影响范围？"
    status: settled
    answer: "3 条记录，3 种格式"
  
  - id: D3
    question: "存储后端确认？"
    status: settled
    answer: "SQLite (内存)"
```

**6 维度收敛**:
```yaml
consensus:
  dimensions:
    goal: locked
    success_criteria: locked
    constraints: locked
    authorization: locked
    exceptions: confirmed
    terminology: confirmed
  gaps_remaining: []
```

#### 3. pax-diagnose: 问题诊断

**根因分析**:
```yaml
diagnosis:
  root_cause:
    statement: "代码中没有统一时间格式的机制"
    confidence: high
    severity: P1
```

#### 4. pax-plan: 方案规划

**任务分解**:
```yaml
plan:
  tasks:
    - id: T1
      title: "添加时间格式统一函数"
      estimated_effort: "30 分钟"
      risk: low
    
    - id: T2
      title: "修改 get_users() 调用统一函数"
      dependencies: [T1]
      estimated_effort: "15 分钟"
      risk: low
    
    - id: T3
      title: "添加测试"
      dependencies: [T2]
      estimated_effort: "15 分钟"
      risk: low
```

#### 5. pax-execute: 执行开发

**执行结果**:
```yaml
execution:
  status: completed
  tasks_completed: 3
  tasks_total: 3
  progress: 100%
```

#### 6. pax-review: 结果验证

**验证结果**:
```yaml
review:
  validation:
    - id: V1
      description: "验证时间格式统一"
      status: pass
      result: "所有时间格式统一为 ISO 8601"
    - id: V2
      description: "验证时区信息保留"
      status: pass
      result: "时区信息保留（+08:00）"
    - id: V3
      description: "验证时间值未改变"
      status: pass
      result: "时间值未改变"
  
  final_assessment:
    success_criteria_met: true
    all_tests_passed: true
    no_regressions: true
    ready_for_merge: true
```

### 快照文件

所有快照文件保存在 `snapshots/` 目录：
- `snapshot_bug2_orchestrate.yaml`
- `snapshot_bug2_clarify.yaml`
- `snapshot_bug2_diagnose.yaml`
- `snapshot_bug2_plan.yaml`
- `snapshot_bug2_execute.yaml`
- `snapshot_bug2_review.yaml`

---

## 示例 2: 用户导出功能开发（feature_dev + pax-test）

### 场景描述

添加用户导出功能，支持 CSV 和 JSON 格式。

### 用户输入

```
添加用户导出功能，支持 CSV 和 JSON 格式
```

### 执行流程

```
pax-orchestrate → pax-clarify → pax-plan → pax-execute → pax-test → pax-review
```

### 详细步骤

#### 1. pax-orchestrate: 意图分类与路由构建

**意图分类**:
- 一级意图: `feature_dev`
- 二级意图: `export`

**风险评分**:
| 维度 | 分数 | 说明 |
|------|------|------|
| 不可逆性 | 1 | 新功能可以回滚 |
| 影响范围 | 2 | 添加新接口 |
| 不确定性 | 2 | 需求需要澄清 |
| 协调成本 | 1 | 单仓库 |
| **总分** | **6** | **low** |

**路由**: `[clarify, plan, execute, review]`

#### 2. pax-clarify: 需求澄清

**设计树**:
```yaml
design_tree:
  - id: D1
    question: "功能的核心目标是什么？"
    status: settled
    answer: "添加用户导出功能，支持 CSV 和 JSON 格式"
  
  - id: D2
    question: "成功标准是什么？"
    status: settled
    answer: "导出功能正常工作，数据完整，格式正确"
```

#### 3. pax-plan: 方案规划

**任务分解**:
```yaml
plan:
  tasks:
    - id: T1
      title: "设计导出接口"
      estimated_effort: "30 分钟"
    
    - id: T2
      title: "实现 CSV 导出"
      dependencies: [T1]
      estimated_effort: "30 分钟"
    
    - id: T3
      title: "实现 JSON 导出"
      dependencies: [T1]
      estimated_effort: "30 分钟"
    
    - id: T4
      title: "添加测试"
      dependencies: [T2, T3]
      estimated_effort: "30 分钟"
```

#### 4. pax-execute: 执行开发

**执行结果**:
```yaml
execution:
  status: completed
  tasks_completed: 4
  tasks_total: 4
  progress: 100%
```

#### 5. pax-test: 自动化测试生成（扩展 Skill）

**测试结果**:
```yaml
tests:
  status: completed
  summary:
    total: 10
    passed: 10
    failed: 0
    skipped: 0
  coverage:
    target: 80
    actual: 85.0
    status: passed
```

#### 6. pax-review: 结果验证

**验证结果**:
```yaml
review:
  validation:
    - id: V1
      description: "验证 CSV 导出"
      status: pass
    - id: V2
      description: "验证 JSON 导出"
      status: pass
    - id: V3
      description: "验证数据完整"
      status: pass
  
  final_assessment:
    success_criteria_met: true
    all_tests_passed: true
    no_regressions: true
    ready_for_merge: true
```

---

## 示例 3: SQL 注入漏洞修复（diagnose_fix + security）

### 场景描述

用户注册接口存在 SQL 注入漏洞，需要修复。

### 用户输入

```
发现用户注册接口存在 SQL 注入漏洞，需要修复
```

### 执行流程

```
pax-orchestrate → pax-clarify → pax-diagnose → pax-plan → pax-execute → pax-review
```

### 详细步骤

#### 1. pax-orchestrate: 意图分类与路由构建

**意图分类**:
- 一级意图: `diagnose_fix`
- 二级意图: `security`

**风险评分**:
| 维度 | 分数 | 说明 |
|------|------|------|
| 不可逆性 | 2 | 代码修改可以回滚 |
| 影响范围 | 3 | 安全漏洞影响所有用户 |
| 不确定性 | 2 | 需要确认漏洞细节 |
| 协调成本 | 2 | 需要修复多个文件 |
| **总分** | **9** | **high** |

**强制升级**: `security` 二级意图 → 强制 `risk: high`

**路由**: `[clarify, diagnose, plan, execute, review]`

#### 2. pax-clarify: 需求澄清

**设计树**:
```yaml
design_tree:
  - id: D1
    question: "问题的具体表现是什么？"
    status: settled
    answer: "用户注册接口存在 SQL 注入漏洞"
  
  - id: D2
    question: "这个问题首次出现的时间？"
    status: settled
    answer: "最近一次代码部署后出现"
  
  - id: D3
    question: "影响范围有多大？"
    status: settled
    answer: "影响所有用户注册，可能导致数据泄露"
```

#### 3. pax-diagnose: 问题诊断

**根因分析**:
```yaml
diagnosis:
  root_cause:
    statement: "代码中使用了字符串拼接 SQL，没有使用参数化查询"
    confidence: high
    severity: P0
```

#### 4. pax-plan: 方案规划

**任务分解**:
```yaml
plan:
  tasks:
    - id: T1
      title: "添加输入验证"
      estimated_effort: "30 分钟"
      risk: low
    
    - id: T2
      title: "使用参数化查询替换字符串拼接"
      dependencies: [T1]
      estimated_effort: "30 分钟"
      risk: low
    
    - id: T3
      title: "添加安全测试"
      dependencies: [T2]
      estimated_effort: "30 分钟"
      risk: low
```

#### 5. pax-execute: 执行修复

**执行结果**:
```yaml
execution:
  status: completed
  tasks_completed: 4
  tasks_total: 4
  progress: 100%
```

#### 6. pax-review: 结果验证

**验证结果**:
```yaml
review:
  validation:
    - id: V1
      description: "验证漏洞已修复"
      status: pass
      result: "SQL 注入攻击已阻止"
    - id: V2
      description: "验证通过安全测试"
      status: pass
      result: "所有安全测试通过"
  
  final_assessment:
    success_criteria_met: true
    all_tests_passed: true
    no_regressions: true
    ready_for_merge: true
    security_verified: true
```

---

## 扩展 Skill 使用

### pax-monitor: 监控

```yaml
monitoring:
  status: active
  config:
    interval: "30s"
    metrics: ["cpu", "memory", "latency"]
  thresholds:
    cpu: 80
    memory: 80
    latency: 1000
```

### pax-rollback: 回滚

```yaml
rollback:
  status: completed
  trigger_reason: "task_failure"
  strategy: "git_revert"
  steps:
    - id: "instance_0"
      type: "git_revert"
      status: "completed"
```

### pax-test: 测试

```yaml
tests:
  status: completed
  summary:
    total: 10
    passed: 10
    failed: 0
  coverage:
    target: 80
    actual: 85.0
```

### pax-deploy: 部署

```yaml
deployment:
  status: completed
  strategy: "rolling"
  environment: "staging"
  pre_checks:
    status: passed
  health_checks:
    status: passed
```

### pax-learn: 学习

```yaml
learning:
  experiences:
    - category: "consensus"
      title: "需求澄清经验"
      content:
        key_insights: [...]
        lessons_learned: [...]
        best_practices: [...]
```

---

## 示例 4: 把一个既有项目接入家族（pax-init，直接调用）

### 场景描述

把一个前后端分离的既有项目接进家族：后端 Spring Boot + RuoYi，前端 Vue 3 + Vite + pnpm。

### 用户输入

```
把 D:/workspaces/ops-pilot 和 D:/workspaces/ops-pilot-web 接入 pax-family
```

### 执行流程

```text
pax-init（直接调用，不经过编排路由）
```

> `pax-init` 是 L4 层内部工具，`requires_snapshot: false`。它不认领路由落点，也不产出任务快照——输入是项目路径，产物是项目级元数据。

### 详细步骤

#### 1. 模式判定（W1）

前后端各自有特征文件 → `multi_project`。先声明：`本次模式=多项目，目标路径=ops-pilot + ops-pilot-web`。

#### 2. 技术栈扫描（W2）

逐项核对 `references/tech-stack-detection.md` 的特征文件，命中即带证据：

| 检测目标 | 证据文件 | 提取内容 |
|---|---|---|
| Java / Maven | `pom.xml` | java 17、`ruoyi-*` 模块清单 |
| Spring Boot | `pom.xml` | `spring-boot-starter-web` 等 starter |
| Vue | `package.json` | vue 3.x、element-plus |
| Vite / TypeScript | `vite.config.ts` / `tsconfig.json` | vite 5.x、ts 5.x |
| 包管理器 | `pnpm-lock.yaml` | pnpm（`package-lock.json` 同时存在 → 写入 `package_manager_note` 并交用户确认） |

未命中的目标一律标「未检测到」，不猜。

#### 3. 代码生成器规范提取（W3）

从后端 `BaseEntity` / `TenantEntity` / 建表模板提取租户字段、审计字段、逻辑删除字段，写入 profile 的 `db_conventions`。

#### 4. 规范文档发现（W4）

若项目已有 `docs/agents/project-standards.md`，只登记**指针 + 摘要**：

```json
{
  "path": "docs/agents/project-standards.md",
  "status": "present",
  "consumption_rule": "下游阶段 MUST 完整阅读该文件后逐条对照执行；冲突时以原文为准",
  "sections": ["coding_standards", "db_conventions"]
}
```

#### 5. AGENTS.md 处置（W5）

- 目标项目无 `AGENTS.md` → 按 `templates/AGENTS.md.tmpl` 渲染后写入。
- 已有 `AGENTS.md` → 展示摘要 + 三选一（覆盖 / 合并 / 跳过），未确认不写入。

#### 6. profile 生成（W6）与 `.pax/` 创建（W7）

```text
<项目根>/AGENTS.md
<项目根>/.pax/project-profile.json
<项目根>/.pax/{plan,execute,review,docs}/
```

#### 7. 交付确认（W8）

```text
本次模式=多项目，目标路径=D:/workspaces/ops-pilot + ops-pilot-web，已扫描，
技术栈=Spring Boot/RuoYi + Vue3/Vite/TS，AGENTS.md=新建，.pax=已创建
```

### 产物与消费方

| 产物 | 消费方 |
|---|---|
| `.pax/project-profile.json` 的 `build_commands` | L1 执行层跑构建 / 测试 |
| `.pax/project-profile.json` 的 `coding_standards` / `db_conventions` | L1 执行层写代码与建表 |
| `.pax/project-profile.json` 的 `standards_doc` 指针 | L1 规划 / 评审层逐条对照项目自有规范 |

---

## 运行示例

```bash
# 家族契约体检
pax-forge test

# 内部路由数据集结构校验（不调 API）
python scripts/validate_internal_routing.py

# 能力评估（真实调用模型，产生费用）——完整说明见 evals/README.md
PYTHONUTF8=1 python evals/run_internal_routing_eval.py --dry-run
PYTHONUTF8=1 python evals/run_internal_routing_eval.py --repeats 5

# 已归档的评估产物
ls evals/results/
```