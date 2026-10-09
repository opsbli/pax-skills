---
name: pax-orchestrate
description: >
    Use when: 所有 pax-family 任务的统一入口。当用户目标涉及诊断修复、功能开发、重构优化、数据操作、文档咨询或工具构建时，必须先经过 pax-orchestrate 进行意图分类、风险分级、路由构建与快照初始化。不要直接选择 pax-diagnose、pax-plan、pax-execute 等具体 skill，而是让 pax-orchestrate 决定完整的执行路由。
version: 1.0.0
family: pax
layer: L0
optional: false
requires_snapshot: true
---

# pax-orchestrate


## Overview

pax-family 统一入口。对每个任务先做意图分类（6 类 MECE 意图）与四维风险评分（不可逆性 / 影响范围 / 不确定性 / 协调成本），再据此构建执行路由并初始化跨 Skill 快照。

## When to Use

所有 pax-family 任务默认从这里开始：诊断修复、功能开发、重构优化、数据操作、文档咨询、工具构建。用户或上层 Agent 明确点名要编排时直接进入。

## Common Pitfalls

- 直接调用 L1 具体 Skill 绕过路由，导致风险分级缺失。
- 高风险动作（部署 / 数据订正 / 破坏性命令）未获得用户明确 approval / confirm 就下发。
- 未初始化快照，下游 Skill 拿不到跨阶段状态。
- 把「门禁文件缺失（schema/versions 不可读）」当成「环境降级」继续执行——门禁失败是硬性拒绝启动，
  不是可降级项；这是本项目曾踩过的实际坑（Agent 在门禁缺失时选择降级继续，绕过编排纪律）。

## Verification Checklist

- [ ] 已完成意图分类且分类结果与 6 类 MECE 表一一对应
- [ ] 已计算四维风险分并标注等级，高风险任务已向用户显式请求 approval / confirm
- [ ] 已初始化快照并把路由表写入快照，可以交给 L1 Skill
## Execution Contract
- 前置门禁：能读取 `pax-family.schema.yaml` 与 `pax-ops/versions.json`
- 未通过门禁：拒绝启动，返回用户错误（`blocked`）
- **门禁失败不是「环境降级」**：为了满足快照与版本门，`pax-family.schema.yaml` / `pax-ops/versions.json`
  缺失时是**硬性拒绝启动**，MUST 返回 `blocked` 并列出缺失项、引导用户先补建 pax-ops 运行时，
  NEVER 以「环境降级」「保证任务不阻塞」等名义继续执行或照常产出编排结论。
- 可降级项（唯一）：版本门自身故障（`pax-ops/versions.json` 无法解析）→ 放行并标注口径；
  这不等于门禁文件缺失可以降级继续。
- 版本检查：`pax-ops/versions.json`
- 记录义务：`diagnose_required` 决策必须附 `rationale`（若跳过诊断则附 `skip_reason`）
- 记录义务：风险评分必须写入四维原始分数与总分
- 记录义务：意图分类必须写入 `intent.primary` 与 `intent.secondary`
- 禁止修改快照下游字段（`consensus` / `diagnosis` / `plan` / `execution` / `review`）

## 职责边界
- 做什么：意图分类（MECE）、风险评分、`diagnose_required` 决策、路由构建、快照初始化
- 不做什么：不执行具体工作、不修改快照下游字段、不产出执行或评审结论

## 输入
- 必需：`user_goal`（用户目标陈述）、`context`（当前上下文）
- 可选：历史快照、领域依赖映射表（`references/domain-dependencies.md`）

## 工作流

### W1 意图分类（MECE Intent Classification）

将 `user_goal` 分类为**一级意图**和**二级意图**。一级意图决定路由主干，二级意图影响诊断深度和验证策略。

#### 一级意图（Primary Intent）

| 意图 | 标识 | 判定条件 | 路由主干 |
|---|---|---|---|
| **诊断修复** | `diagnose_fix` | 用户报告异常/报错/退化，需要找根因再修 | `[clarify, diagnose, plan, execute, review]` |
| **功能开发** | `feature_dev` | 新建功能、修改功能行为，无既有缺陷 | `[clarify, plan, execute, review]` |
| **重构优化** | `refactor` | 不改变外部行为，改善内部结构/性能 | `[clarify, plan, execute, review]` |
| **数据操作** | `data_ops` | 数据订正、迁移、批量修改 | `[clarify, diagnose, plan, execute, review]` |
| **文档咨询** | `doc_consult` | 纯文档、纯咨询、纯规划、纯解释 | `[clarify, docs]` |
| **工具构建** | `tool_build` | 构建工具、脚本、自动化 | `[clarify, plan, execute, review]` |

#### 二级意图（Secondary Intent）

二级意图不改变路由主干，但影响诊断深度和验证策略：

| 二级意图 | 触发条件 | 影响 |
|---|---|---|
| `performance` | 性能退化、延迟增加、吞吐量下降 | 诊断必须包含性能指标采集 |
| `security` | 安全漏洞、权限异常、数据泄露、涉及具体敏感字段（身份证号、手机号、支付凭证、密码、银行卡号等）的查看/修改/存储 | 强制升级决策层，P0 候选 |
| `data_integrity` | 数据不一致、数据丢失、字段错误 | 诊断必须包含存储后端确认 |
| `ux_error` | 前端报错、交互异常、UI 缺陷 | 需标注跨仓库（前后端分离时） |
| `integration` | 集成故障、API 对接异常 | 需确认依赖版本和接口契约 |
| `deployment` | 部署失败、配置错误、环境差异 | 需确认目标环境差异 |

**易混淆边界**：`ux_error` 仅指缺陷位于**前端展示或交互层**（渲染错误、状态不同步、
点击无响应、UI 布局错乱）。字段值未通过正则/格式/长度校验而报错，即使错误提示出现在页面，
根因在数据契约或校验规则本身，归入 `data_integrity`，**不标** `ux_error`。

**易混淆边界**：新增功能**涉及具体敏感字段**（身份证号、手机号、支付凭证、密码、银行卡号等）
的查看/修改/存储，即使本身没有已发生的安全漏洞或数据泄露，也归入 `security`——
这类功能的安全设计（鉴权、脱敏、审计）必须在诊断/规划阶段前置评估。
仅出现「用户列表 / 用户数据 / 导出报表」等泛化表述、未明确具体敏感字段的，
**不算** `security`（除非同时命中安全漏洞/权限异常/数据泄露）。

#### 分类规则

```python
def classify_intent(user_goal, context):
    """MECE 意图分类，返回 (primary, secondary)"""
    
    # Step 1: 检测是否为诊断类（最高优先级）
    if has_defect_signal(user_goal):
        primary = "diagnose_fix"
    elif is_data_operation(user_goal):
        primary = "data_ops"
    elif is_pure_documentation(user_goal):
        primary = "doc_consult"
    elif is_refactoring(user_goal):
        primary = "refactor"
    elif is_tool_building(user_goal):
        primary = "tool_build"
    else:
        primary = "feature_dev"  # 默认
    
    # Step 2: 检测二级意图（可叠加）
    secondaries = detect_secondary_intents(user_goal, context)
    
    return primary, secondaries
```

**诊断类信号检测**（`has_defect_signal`）：

以下关键词组合中出现 ≥2 项时判定为诊断类：

- 异常/报错/错误/异常/失败/不可用/挂了/崩溃
- 修复/修/解决/处理/排查/定位
- 最近/之前/突然/一直/间歇/偶发
- 报错信息/堆栈/日志/trace/error/exception

**数据操作信号检测**（`is_data_operation`）：

- 订正/修正/修复数据/清理数据
- 迁移/转换/批量更新/批量修改
- 数据不一致/数据丢失/字段错误/脏数据

**文档咨询信号检测**（`is_pure_documentation`）：

- 纯文档/写文档/更新文档/README
- 咨询/解释/分析/调研/了解
- 规划/设计/方案/估算
- 不涉及代码修改或数据变更

### W2 风险评分（Risk Assessment）

四维评分，每项 1–3 分，总分 4–12。

#### 不可逆性（Irreversibility）

| 分数 | 判定标准 | 示例 |
|---|---|---|
| 1 | 可轻易回滚，无需外部协调，且不触发部署流程 | 代码修改（未上线的本地改动）、配置修改（有备份，不触发部署）、文档修改 |
| 2 | 可回滚但需要步骤或工具 | 前端/后端部署（可回退）、数据库迁移（有 down 脚本）、API 变更（有兼容层） |
| 3 | 不可逆或回滚成本极高 | 数据删除/覆盖、生产部署无回滚计划、安全凭证更换、大规模数据迁移 |

**边界**：改动需要部署上线才能生效的，即使可回滚也至少算 2；
不需要部署流程的配置/文档/本地代码修改算 1。
「大规模数据迁移」的阈值与影响范围基准一致：跨 ≥5 张表或数据量 ≥1000 万行算 3。
数据操作：有完整备份的单表填充/订正算 1；多表数据订正算 2；
物理删除/覆盖或大规模迁移算 3。不因是「生产环境」就升分。
判据的顿号语义：3 档「不可逆或回滚成本极高」满足任一即算。

#### 影响范围（Impact Scope）

| 分数 | 判定标准 | 示例 |
|---|---|---|
| 1 | 单模块、单使用人、无外部依赖 | 内部工具（仅本人使用）、个人脚本、单模块文档 |
| 2 | 多模块、多使用人、有内部依赖 | 跨模块功能、API 接口变更、多使用人共享的内部工具 |
| 3 | 系统级、跨团队、跨系统、全用户 | 核心链路、跨团队依赖、外部系统集成、所有用户 |

**边界**：「内部工具」按实际使用人数判定——仅本人使用算 1；
有多个使用人（含团队内多组共用）按「多使用人」算 2。
判据的顿号语义：1 档全部条件须同时满足；2 和 3 档满足任一即算。

**数据类任务的影响范围基准**：影响范围按**受影响的业务面**判定，不按改动文件数。
- 1：内部工具、单次实验数据、仅本人可见
- 2：单张表、测试/预发环境、仅本团队可见的数据
- 3：满足任一项 —— 跨 ≥5 张表或数据量 ≥1000 万行；覆盖用户核心操作链路
  （登录、支付、账务、资产台账、下单、库存、商品详情等）；或全公司/全客户可见

不因“是数据迁移”就默认 3；也不因“只改了一张表”就默认 1。

#### 不确定性（Uncertainty）

| 分数 | 判定标准 | 示例 |
|---|---|---|
| 1 | 需求明确、方案清晰、风险可控 | 有明确规格的需求、已知模式的修改、有先例可循 |
| 2 | 部分不确定、需要探索 | 部分需求未明确、需要验证假设、新库/新框架 |
| 3 | 高度不确定、探索性、无先例 | 全新领域、技术选型未定、需求模糊、根因未知 |

**边界**：
- 需要产品/需求方确认任何一项（含交互细节）即至少算 2。
- 需要验证**一个未验证的假设**（调用顺序、性能、边界行为等）再上线的算 2；
  照既有脚本/手册执行、验证方式已知的算 1 的「有先例可循」。
- 数据操作：prompt 写「标准流程/操作手册/有先例」的算 1，不因是生产环境就升 2。
- 判据的顿号语义：1 档全部条件须同时满足；2 和 3 档满足任一即算。

#### 协调成本（Coordination Cost）

| 分数 | 判定标准 | 示例 |
|---|---|---|
| 1 | 单人可完成、无需协调 | 单模块修改、单人工具、独立文档 |
| 2 | 需要模块内协调、跨文件修改 | 跨文件重构、前后端联动（同仓库）、需要 code review |
| 3 | 需要跨团队协调、跨仓库操作 | 跨仓库操作、跨团队依赖、需要架构评审、需要发布协调 |

**边界**：
- 「跨文件修改」指多文件联动的实质重构（前后端联动、跨模块接口改造），
  不是字面的「改动了 ≥2 个文件」。prompt 明确写「单人完成／不需要其他人配合」的，
  以「单人可完成」为准判 1，不因改动文件数升 2。
- 数据操作：任务本身单人可完成（改一个脚本/工具/配置）算 1，即使多人使用；
  使用人数归影响范围，不归协调成本。
- 判据的顿号语义：1 档全部条件须同时满足；2 和 3 档满足任一即算。

#### 数据操作类任务的评分基准

涉及数据订正、迁移、清理、填充等操作时，四个维度按以下基准判定：

| 维度 | 1 档 | 2 档 | 3 档 |
|------|------|------|------|
| 不可逆性 | 有备份的单表填充/订正 | 多表数据订正（可回滚但需步骤） | 物理删除/覆盖；跨 ≥5 表或 ≥1000 万行的大规模迁移 |
| 不确定性 | 标准流程/手册/有先例 | 需验证未验证的假设 | 无先例、根因未知 |
| 协调成本 | 单人可完成（使用人数归影响范围） | 需 code review 或跨模块联动 | 跨团队、跨仓库 |

**核心原则**：不因是「生产环境」就自动升分。备份、标准流程、单人完成是降档依据。

#### 总分映射

| 总分 | 等级 | `required_precision` | `question_strategy` |
|---|---|---|---|
| 4–6 | 低 | `low` | `batch` |
| 7–9 | 中 | `medium` | `batch` |
| 10–12 | 高 | `high` | `one-by-one` |

实现时用 `precision_from_total(risk.total)` 取 `required_precision`，
**不要**在 `risk` 对象上另造 `precision` 字段（该名字不存在）。

#### 强制升级规则

以下情况无论总分多少，均强制升级：

- 二级意图包含 `security` → 强制 `risk: high`，标记 `escalate_to_council: true`
- 二级意图包含 `data_integrity` 且影响范围为 3 → 强制 `risk: high`
- 不可逆性为 3 且影响范围为 3 → 强制 `risk: high`

命中任一条时，MUST 在 `risk.forced_escalation` 写 `true`（未命中写 `false`），
并把 `level` 覆盖为 `high`，同时写入 `annotations.escalate_to_council: true`。
`forced_escalation` 与 `level` 都会被 `init_snapshot` 原样写入快照，是审计依据。

### W3 诊断必要性决策（Diagnose Required Decision）

```python
def is_diagnostic_intent(intent, context):
    """判断是否需要进入诊断阶段"""
    
    # 强制诊断
    if intent.primary in ("diagnose_fix", "data_ops"):
        return True
    
    # 强制跳过
    if intent.primary == "doc_consult":
        return False, "纯文档/咨询/规划类任务"
    
    # 条件判断
    if intent.secondary and "security" in intent.secondary:
        return True, "安全相关问题必须诊断根因"
    
    if intent.secondary and "data_integrity" in intent.secondary:
        return True, "数据完整性问题必须诊断根因"
    
    # 新功能/重构/工具 → 默认跳过诊断
    if intent.primary in ("feature_dev", "refactor", "tool_build"):
        return False, "新建功能/重构/工具构建，无既有行为缺陷"
    
    # 默认：需要诊断
    return True, "存在既有行为异常信号"
```

#### 跳过诊断的允许条件

必须显式记录 `skip_reason`，允许条件：

| 条件 | `skip_reason` 值 |
|---|---|
| 新建功能，无既有行为 | `new_feature_no_prior_behavior` |
| 根因已在 clarify 阶段完全确定且用户确认 | `root_cause_pre_determined_by_user` |
| 纯文档、纯咨询、纯规划 | `doc_consult_only` |
| 用户明确要求"先别查根因，直接改" | `user_explicit_skip` |
| 纯重构，不改变外部行为 | `refactor_no_behavior_change` |
| 纯工具/脚本构建 | `tool_build_no_prior_behavior` |

#### 强制诊断条件

以下情况**不允许**跳过诊断：

- `intent.primary == "diagnose_fix"`（有明确缺陷信号）
- `intent.primary == "data_ops"`（数据操作）
- `intent.secondary` 包含 `security` 或 `data_integrity`
- 用户报告了具体的错误信息或异常行为

### W4 路由构建（Route Building）

```python
def build_route(intent, diagnose_required, risk, context):
    """构建完整路由，包括升级标注"""
    
    # 主干路由
    if intent.primary == "doc_consult":
        route = ["clarify", "docs"]
    elif diagnose_required:
        route = ["clarify", "diagnose", "plan", "execute", "review"]
    else:
        route = ["clarify", "plan", "execute", "review"]
    
    # 标注：高风险升级
    if risk.level == "high":
        annotations = {
            "escalate_to_council": True,
            "council_trigger": "high_risk_task"
        }
    
    # 标注：安全相关强制升级
    if "security" in intent.secondary:
        annotations["escalate_to_council"] = True
        annotations["council_trigger"] = "security_relevant"
    
    # 标注：数据操作需存储后端确认
    if intent.primary == "data_ops" or "data_integrity" in intent.secondary:
        annotations["storage_backend_required"] = True
        annotations["script_language_required"] = True
    
    # 标注：跨仓库操作
    if is_cross_repo(context):
        annotations["cross_repo"] = True
        annotations["execution_strategy_required"] = True
        # 标注涉及的仓库
        annotations["involved_repos"] = detect_involved_repos(context)
    
    # 标注：需要前端参与
    if "ux_error" in intent.secondary:
        annotations["frontend_involved"] = True
    
    # 标注：其余二级意图各自要求的验证前置
    if "performance" in intent.secondary:
        annotations["performance_metrics_required"] = True
    if "integration" in intent.secondary:
        annotations["integration_contract_required"] = True
    if "deployment" in intent.secondary:
        annotations["deployment_env_required"] = True
    
    return route, annotations
```

#### 代表路由组合

下表列举常见组合；完整逻辑由 `build_route` 派生（6 个一级意图 × 6 个二级意图的笛卡尔积），
不逐一列举——与上表冲突时以 `build_route` 为准。

| 一级意图 | 二级意图 | diagnose_required | 路由 | 标注 |
|---|---|---|---|---|
| `diagnose_fix` | — | true | `[clarify, diagnose, plan, execute, review]` | — |
| `diagnose_fix` | `security` | true | `[clarify, diagnose, plan, execute, review]` | `escalate_to_council` |
| `diagnose_fix` | `data_integrity` | true | `[clarify, diagnose, plan, execute, review]` | `storage_backend_required` |
| `diagnose_fix` | `ux_error` | true | `[clarify, diagnose, plan, execute, review]` | `frontend_involved` |
| `data_ops` | — | true | `[clarify, diagnose, plan, execute, review]` | `storage_backend_required` |
| `data_ops` | `data_integrity` | true | `[clarify, diagnose, plan, execute, review]` | `storage_backend_required` |
| `feature_dev` | — | false | `[clarify, plan, execute, review]` | — |
| `feature_dev` | `security` | true | `[clarify, diagnose, plan, execute, review]` | `escalate_to_council` |
| `refactor` | — | false | `[clarify, plan, execute, review]` | — |
| `doc_consult` | — | false | `[clarify, docs]` | — |
| `tool_build` | — | false | `[clarify, plan, execute, review]` | — |
| 任意 | 跨仓库 | 继承 | 继承 | `cross_repo, execution_strategy_required` |

#### 跨仓库检测

```python
def is_cross_repo(context):
    """检测是否涉及跨仓库操作

    按词边界匹配，不做裸子串匹配：裸子串会让 "web" 命中 webhook、
    "api" 命中 rapid/capital，造成系统性误判。
    项目自有的仓库名不在此硬编码——写进 references/domain-dependencies.md。
    """
    patterns = [
        r"前端", r"后端", r"跨仓库", r"多仓库", r"微服务",
        r"另一个仓库", r"另一个服务", r"另一个项目",
        r"\bweb\b", r"\brepo\b",
    ]
    return any(re.search(p, context, re.IGNORECASE) for p in patterns)

def detect_involved_repos(context):
    """检测涉及的仓库列表（与 is_cross_repo 的信号保持一致）"""
    repos = []
    if re.search(r"前端|\bfrontend\b", context, re.IGNORECASE):
        repos.append("frontend")
    if re.search(r"后端|\bbackend\b|\bserver\b|\bapi\b", context, re.IGNORECASE):
        repos.append("backend")
    return repos
```

### W5 快照初始化（Snapshot Initialization）

```python
def precision_from_total(total):
    """W2 总分映射：4–6 low / 7–9 medium / 10–12 high"""
    if total <= 6:
        return "low"
    if total <= 9:
        return "medium"
    return "high"


def init_snapshot(intent, risk, diagnose_required, strategy, route, annotations):
    """初始化 pax-snapshot.yaml"""
    
    snapshot = {
        "meta": {
            "version": 1.0,
            "created_at": "<ISO8601>",
            "updated_at": "<ISO8601>",
            "skill_lineage": ["pax-orchestrate"]
        },
        "goal": {
            "statement": "<user_goal>",
            "success_criteria": []  # 由 pax-clarify 填充
        },
        "consensus": {
            "required_precision": precision_from_total(risk.total),  # low | medium | high
            "dimensions": {
                "goal": "unknown",
                "success_criteria": "unknown",
                "constraints": "unknown",
                "authorization": "unknown",
                "exceptions": "unknown",
                "terminology": "unknown"
            },
            "design_tree": [],
            "gaps_remaining": []
        },
        "orchestration": {
            "intent": {
                "primary": intent.primary,
                "secondary": intent.secondary,
                "classification_rationale": "<分类理由>"
            },
            "risk": {
                "irreversibility": risk.irreversibility,
                "impact_scope": risk.impact_scope,
                "uncertainty": risk.uncertainty,
                "coordination_cost": risk.coordination_cost,
                "total": risk.total,
                "level": risk.level,  # low | medium | high
                "forced_escalation": risk.forced_escalation  # true | false
            },
            "diagnose_required": diagnose_required,
            "rationale": "<诊断必要性理由>",
            "skip_reason": "<跳过诊断原因>" if not diagnose_required else None,
            "route": route,
            "question_strategy": strategy,
            "annotations": annotations
        }
    }
    
    # 条件性字段
    if diagnose_required:
        snapshot["symptom"] = {
            "description": "<待 pax-clarify 填充>",
            "impact": "<待 pax-clarify 填充>",
            "reproduction": "<待 pax-clarify 填充>",
            "first_observed": None,
            "recent_changes": []
        }
    
    return snapshot
```

## 风险评分维度

详见 W2 风险评分。

| 维度 | 范围 | 说明 |
|---|---|---|
| 不可逆性 | 1–3 | 变更能否回滚，回滚成本多高 |
| 影响范围 | 1–3 | 影响多少模块、用户、团队 |
| 不确定性 | 1–3 | 需求/方案/根因的明确程度 |
| 协调成本 | 1–3 | 需要多少人/团队/仓库协调 |

## 路由规则

详见 W3 诊断必要性决策 和 W4 路由构建。

## 输出契约
- `snapshot.orchestration`（含 `intent` / `risk` / `diagnose_required` / `route` / `annotations`）
- 快照初始状态（`meta` / `goal` / `consensus`），格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 分类置信度低 → 降级为保守评分（假设高风险），并在路由中保留高风险标记
- 风险维度数据缺失 → 降级为保守评分（假设高不确定性）
- 用户目标过于模糊 → 进入澄清阶段后再路由（先走 `clarify`，`diagnose_required` 设为 `null` 待后续决定）
- 意图分类不确定（多意图重叠）→ 取最高风险意图，并在 `classification_rationale` 中记录歧义
- 检测到安全相关信号但未确认 → 保守标记 `security` 二级意图，强制 `diagnose_required: true`
- **门禁文件缺失（`pax-family.schema.yaml` / `pax-ops/versions.json` 不可读）→ 返回 `blocked`，
  列出缺失项并引导用户先补建 pax-ops 运行时；NEVER 以降级继续顶替。**

## 可选扩展 Skill

除主路由外，以下可选 Skill 可在特定条件下被调用：

| Skill | 层级 | 触发条件 | 说明 |
|---|---|---|---|
| `pax-monitor` | L1 | 任务执行中 | 监控任务执行过程中的异常情况 |
| `pax-rollback` | L1 | 任务失败或严重问题 | 自动化回滚到安全状态 |
| `pax-test` | L1 | 任务执行完成后 | 自动生成测试用例并执行 |
| `pax-deploy` | L1 | 任务完成后 | 自动化部署流程 |
| `pax-learn` | L1 | 任务评审完成后 | 经验沉淀和知识图谱构建 |

### 扩展路由调用规则

#### pax-monitor（监控）
- **触发条件**：任务执行中，需要监控异常情况
- **调用时机**：`pax-execute` 执行过程中
- **输出**：`snapshot.monitoring`

#### pax-rollback（回滚）
- **触发条件**：任务失败、监控告警、用户请求
- **调用时机**：任务执行失败或严重问题时
- **输出**：`snapshot.rollback`

#### pax-test（测试）
- **触发条件**：任务执行完成后，需要验证
- **调用时机**：`pax-execute` 完成后
- **输出**：`snapshot.tests`

#### pax-deploy（部署）
- **触发条件**：任务完成后，需要部署
- **调用时机**：`pax-review` 完成后
- **输出**：`snapshot.deployment`

#### pax-learn（学习）
- **触发条件**：任务评审完成后
- **调用时机**：`pax-review` 完成后
- **输出**：`snapshot.learning`

### 完整工作流示例

主干（顺序固定）：

```
[clarify] → [diagnose] → [plan] → [execute] → [review] → [learn]
```

按条件挂载的 skill（触发条件见上表，不改变主干顺序）：

```
[execute] ── 执行期间 ──────────→ [monitor]
[execute] ── 完成后 ────────────→ [test]
[execute] ── 失败 / 告警 / 用户要求 ─→ [rollback]
[review]  ── 通过后 ────────────→ [deploy]
[review]  ── 评审后 ────────────→ [learn]
任意阶段  ── annotations.escalate_to_council ─→ [council]
```

## 何时升级
- `risk.level == high` → 在路由中标注 `escalate_to_council: true`，由下游阶段协调升级决策
- `intent.secondary` 包含 `security` → 强制标注 `escalate_to_council: true`
- `intent.secondary` 包含 `data_integrity` 且 `risk.impact_scope == 3` → 强制标注 `escalate_to_council: true`
- 意图分类置信度极低 → 返回用户确认意图，再重新路由
