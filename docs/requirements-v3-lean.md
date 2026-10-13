# pax-family 全流程能力精简需求文档（v3）

**文档版本**：v3.0（精简版，取代 v2.1 草案）
**状态**：正式草案
**建议路径**：`docs/requirements-v3-lean.md`
**目标读者**：pax-skills 维护者、Skill 作者、`pax-orchestrate` 路由设计者、评估体系维护者
**基线仓库**：`opsbli/pax-skills` @ `main`（family **1.3.0**，22 skill：含 `pax-analyze` / `pax-design` / `pax-gate`，12 条契约全绿）

---

## 0. 与 v2.1 的差异（本版核心立场）

v2.1 提出 **19 个新 skill**。本版裁定：**其中大多数已以别的形态存在、或彼此重叠、或违反家族硬约束**，因此——

| 项 | v2.1 | v3 处置 |
|---|---|---|
| 新增 skill | 19 个 | **2 个**（`pax-research`、`pax-prototype-to-prd`）+ `pax-design` 前端扩展（并入，不新增） |
| 目标规模 | 22 → ~41 | **22 → ~25** |
| 已落地能力 | 当作"缺失"重复设计 | 明确接线/复用（analyze/design/gate 已在仓库 HEAD） |
| 运行时与仓库 | 未区分 | 新增 **M0：先同步运行时到仓库 HEAD**（已安装副本落后，缺 analyze/design/gate） |

**已锁定决策**（用户裁定，v3 起生效）：

1. **日常任务（日程/笔记/生活事务）不单独进路由**，pax-family 保持"纯软件开发流程"定位，不新增 `personal_ops` 类意图。
2. **前端设计并入 `pax-design`**（作为其前端产出阶段），不新增独立 `pax-frontend-design` skill。

---

## 1. 能力裁定总表

### 1.1 保留为新 skill（3 件事，2 个新 skill + 1 处扩展）

| # | 能力 | 形态 | 层级 | 优先级 | 备注 |
|---|---|---|---|---|---|
| N1 | 需求调研 / 竞品比对 / 技术选型（**信息采集**） | 新增 `pax-research` | L1 可选 | P0 | 只做采集→候选；评估/裁决归 advisor |
| N2 | 原型 → 结构化 PRD（含 EARS 验收标准、质量门禁、变更管理） | 新增 `pax-prototype-to-prd` | L1 可选 | P0 | validator/change 作为其内部阶段，不独立 |
| N3 | 前端样式/风格一致性/设计系统检测 | 扩展 `pax-design`（前端产出阶段） | L1 | P1 | design-system-detect 作为内部步骤 |

### 1.2 融合（不新增，并入现有 skill）

| v2.1 提议 | 并入目标 | 增强点 |
|---|---|---|
| `pax-security` + `pax-a11y-i18n` + `pax-compliance` + 许可证 | **已有 `pax-gate`** | 能力已是 gate 的承载体，仅需接线进 review/deploy 路由，**零新增** |
| `pax-db-migration` | `pax-diagnose` / `pax-rollback` / `pax-plan.rollback_strategy` | 在 `pax-test` 补 migration up/down 实跑校验；`pax-rollback` 补迁移可逆性检查项 |
| `pax-incident` | `pax-monitor` + `pax-learn` + 接线 `pax-evolve` | 告警→复盘→沉淀链路接线，不新建 |
| `pax-self-audit` | **接线 `pax-evolve`** | evolve 已有 OODA/A-B/回滚；自审是 its 触发器 |
| `pax-cicd` | `pax-deploy` 增强 | 环境差异检测 + 流水线生成/校验并入部署 |
| `pax-refactor` | 增强 `pax-review` + 既有 `refactor` 意图 | review 补行为等价性断言 |
| `pax-tech-stack-selector` | **并入 `pax-research`** | 技术选型是 research 产物的子项 |
| `pax-prd-validator` / `pax-prd-change` | **并入 `pax-prototype-to-prd`** | 质量门禁=出口阶段；变更管理=横切阶段 |
| `pax-design-system-detect` | **并入 `pax-design` 前端阶段** | 内部检测步骤 |
| `pax-memory` | **不占 L0**；增强 `pax-docs`（THINKING）+ `pax-learn`（经验） | L0 是 `optional:false` 强制单一入口，承载记忆层是契约冲突 |
| `pax-domain-pack` | 并入 `pax-orchestrate` 扩展注册机制 | 路由层可扩展点，非家族 skill |

### 1.3 接线（能力已存在但未入路由）

| 项 | 现状 | 动作 |
|---|---|---|
| `pax-evolve` | SKILL.md 已 `status: active`，但无 L1 调用 | 由 orchestrate 在 learn 之后登记触发（承接自审/复盘进化） |
| `pax-advisor` | 仅 analyze 升级路径接线 | 扩展接线到 `pax-research`（选型评估）与 `pax-design`（方案评审） |

### 1.4 删除 / 放弃

| 项 | 处置 |
|---|---|
| `pax-fullstack-builder` | **放弃**（反模式：端到端一把梭，与分工/门禁/评审哲学冲突；最多留作脚手架模板） |
| 8 个骨架评估数据集（deploy/execute/monitor/plan/review/rollback/test/verify） | **删除或补齐**：各 3 题 + TODO 占位会误报"已覆盖"。优先参照 `pax-design`（15 题真数据 + 变异测试）补齐 8 个主线环节 |

### 1.5 明确不做（v2.1 已确认）

- 移动端 / K8s / MLOps：下游领域包，经 orchestrate 扩展点接入，不进主干分层。
- 日常任务路由：本次锁定不做。

---

## 2. 硬约束（不可违反，设计前置）

沿用家族既有契约，任何新增/扩展必须通过 12 条契约：

| 约束 | 要求 |
|---|---|
| 快照顶层封闭 | `snapshot.schema.json` 为 `additionalProperties: false`。新增能力**优先复用既有段**（`consensus` / `design` / `analysis` / `plan`）；必须新增时做一次**批量 minor bump**（family 1.3.0 → 1.4.0），不逐个零散加段 |
| 段所有权 | 每个顶层段由唯一 skill 独占写入，不双写 |
| L4 是叶子层 | 横切检查（安全/合规/a11y）由 L1 在指定阶段调用，不做 L4 主动下探 |
| L0 单一入口 | `pax-orchestrate` 是唯一 L0（`optional:false`）；记忆层等可选能力不得占 L0 |
| 无环 | 跨阶段协作写阶段名（数据流），不写 skill 名成边 |
| 门禁 fail-closed | 门禁失败硬拒绝，不允许部分冻结/降级继续 |
| AI 输出为候选 | research 产出一律 `*_candidates` + `confidence`，经 clarify/设计/review 确认后才可冻结 |
| 接线优先于新建 | 已存在但未接入的能力先接线，验证不足再新建 |

---

## 3. 新增能力详设

### 3.1 `pax-research`（L1，开发前发现阶段）

**定位**：从模糊需求出发，完成外部信息采集——需求背景调研、竞品比对、技术选项——产出**可交接的候选集**，供下游评估与裁决。**不冻结任何结论**。

**触发条件**：
- `feature_dev` / `tool_build` 且风险评分 `uncertainty >= 2`，或用户表达"调研/看竞品/选型/值不值得做"。
- `pax-clarify` 识别到高不确定性需求，请求研究。

**挂载点**：`clarify` 之前或并行（`research_required` 标注时插入），产出接 `consensus` 与 `design.candidates`。

**快照承接**：复用 `analysis` 段语义扩展（加 `mode: research` 判别），或批量 minor bump 新增可选顶层 `research` 段：

```yaml
research:
  question: string
  scope: string
  sources: [{url, type, credibility}]
  findings: [{claim, evidence, confidence}]        # 全部候选
  competitors: [{name, features, pricing, positioning}]
  alternatives: [{option, pros, cons, score}]       # 候选方案，未经确认
  recommendation_candidate: string                  # 候选，非结论
  confidence: high|medium|low
  open_questions: [string]
```

**职责**：采集 → 组织候选 → 交接。**不裁决**；技术选型评估移交 `pax-advisor`（A2/A3 证据加权），方案定稿移交 `pax-design`。

**依赖**：`pax-worker-research`（L3 执行子任务）、`pax-advisor`（评估）、`pax-council`（高风险选型盲审）。

**验收标准**：
- 对"消息队列选型"产出 ≥3 个候选与对比矩阵，每项可回溯来源并标可信度。
- 所有结论以候选形式写入 `research`/`analysis` 段，无 `confirmed` 结论。
- 快照可被 `pax-advisor` 与 `pax-design` 直接消费。
- 配数据集 + runner + 变异测试（遵循家族"新能力必配评估"强制项）。

### 3.2 `pax-prototype-to-prd`（L1，需求工程上游）

**定位**：从原型（HTML/截图/Figma/Axure 导出）生成结构化 PRD，并内建**质量门禁**与**变更管理**两个阶段，作为 PRD 工程链路唯一入口。

**触发条件**：
- 用户"原型转 PRD / 生成 PRD / 解析原型"。
- 需求工程链路（产品型/日常开发）需要 PRD 作为契约锚点。

**挂载点**：`clarify` 阶段内或之前；产出 PRD 后按需进入 `pax-design` / `pax-plan`。

**核心流程（单 skill 三段）**：
1. **生成**：原型解析（多工具识别）→ 功能提炼 → EARS 验收标准生成 → 数据字典 → 页面流转图 → 竞品（可调用 `pax-research`）→ 组装 PRD。
2. **校验（内置门禁）**：必备章节完整 / EARS 格式 / NFR 可衡量 / In-Out scope 明确 → `PASS|NEEDS_WORK|FAIL`；`FAIL` 阻断进入 `pax-design`（fail-closed）。
3. **变更管理（内置横切）**：PRD 更新 → 影响分析（设计/任务/测试）→ 变更分类（新建/更新/无需操作）→ 变更提案 → 用户批准 → 传播下游。

**快照承接**：批量 minor bump 新增可选顶层 `prd` 段：

```yaml
prd:
  source: {type, path, pages}
  features: [{id, name, module, priority}]
  functional_requirements:
    - {id, ears, acceptance: {given, when, then}, priority: must|should|could}
  acceptance_criteria: [{id, ears, testable}]
  data_dictionary: [{field, type, required}]
  scope: {in, out}
  verification: {verdict: PASS|NEEDS_WORK|FAIL, findings: [...]}
  change: {change_id, type, impact_analysis, status: pending_approval|approved|applied}
```

**依赖**：`pax-research`（竞品/技术背景）、`pax-clarify`、`pax-memory`（PRD 持久化，经 `pax-docs` 落地）。

**验收标准**：
- "智能运维工作台"原型 → 提取 ≥5 功能模块 → EARS 验收标准 → 校验 PASS。
- 缺失必备章节或 EARS 违规时阻断进入 design。
- 变更在用户批准前不传播任何下游。
- 配数据集 + runner + 变异测试。

### 3.3 `pax-design` 前端扩展（N3，不新增 skill）

**定位**：在现有 `pax-design` D 系列之上增加**前端产出阶段**，保障新页面与既有项目风格一致，或为 0-1 项目建立视觉方向。

**增量**：
- 内部步骤 `design-system-detect`：框架/样式方案识别 → 设计令牌提取 → 组件库识别 → 输出设计上下文（可写 `memory/DESIGN.md`）。
- 风格一致性：消费/生成 DESIGN 上下文，新页面与既有令牌匹配。
- 反 AI 套路：内置"生成式设计特征"规避清单（避免 Inter 字体/紫色渐变/居中布局等）。
- 0-1 视觉方向：2-3 个方向供选。
- 视觉验证：浏览器截图自评。

**快照承接**：扩展既有 `design` 段（`frontend: {design_system_ref, visual_direction, components, pages, a11y_checks, visual_verification}`），随 3.1/3.2 同批 minor bump。

**验收标准**：
- 新页面与现有项目设计令牌一致。
- 0-1 项目产出 ≥2 个视觉方向，通过视觉验证且无 AI 套路特征。
- 通过 `layer-call-legality` / `no-cycles`。

---

## 4. 里程碑（阻断项优先）

### M0 — 运行时同步（零新增，最高优先级）

**背景**：已安装运行时副本（19 skill，`doc_consult → [clarify, docs]`）落后于仓库 HEAD（22 skill，`[clarify, analyze]`）。此前落地 analyze/design/gate 未进入运行环境。

**内容**：同步运行时到仓库 HEAD；核验 22 skill 全部可被加载、orchestrate 门禁通过。
**出口判据**：已安装副本 == 仓库 HEAD，`pax-forge test` 12/12。

> **不做 M0 就谈新增，等于在过时底座上盖新楼。** 本版所有新增技能均应以同步后的运行时为基线。

### M1 — `pax-research`

内容：SKILL.md + research 段 schema（随 minor bump）+ 挂载 orchestrate `research_required` 标注 + 接线 advisor/council。
验收：M0 + 数据集/runner/变异测试 + 端到端选型用例。

### M2 — `pax-prototype-to-prd`

内容：SKILL.md + prd 段 schema + 三阶段（生成/校验/变更）+ 接线 clarify/license 门禁。
验收：M0 + 端到端"原型→PRD→design"用例。

### M3 — `pax-design` 前端扩展 + 收尾融合

内容：design 前端段扩展；执行 §1.2 融合清单（db-migration→test/rollback、incident→monitor/learn+evolve、cicd→deploy、refactor→review、self-audit→evolve、advisor 接线）；补齐或删除 8 个骨架数据集。
验收：M0 + 全量契约 12/12。

---

## 5. 非功能需求

| 类别 | 需求 |
|---|---|
| 契约 | 全程 `pax-forge test` 12/12，无非法调用边、无环、无 `snapshot.<段>` 越界 |
| 可评估 | 每个新增能力配数据集 + runner + 变异测试（≥8 变异体全杀）+ 能力分门槛按契约确定性分档 |
| 兼容 | 不改 `pax-orchestrate` W1–W4 契约文本；快照段扩展批量 minor bump，不破坏既有段 |
| 精简 | 家族规模控制在 ~25 skill；任何"又一个新 skill"提议须先过 §2 硬约束 + 接线优先原则 |
| 诚实 | 未真跑的评估不报数字；探针输出仅作线索，结论回验原文 |

---

## 6. 开放问题（待裁定，不影响 M0/M1 起步）

| # | 问题 | 建议默认 |
|---|---|---|
| O1 | `prd` / `research` 段是独立顶层段还是并入既有段？ | 批量 minor bump 新增两个可选顶层段，字段向后兼容 |
| O2 | `pax-research` 是否需要真实外部搜索工具，还是本期只定义契约？ | 本期只定义接口与候选契约，工具适配后续（对齐家族"框架先行"） |
| O3 | PRD 变更传播是否需用户逐一批准？ | 是（对齐"AI 出候选、人工确认"） |
| O4 | 8 个骨架数据集：删还是补？ | 补（都是主线必经环节），删作为保底 |

---

## 7. 验收标准

### 7.1 批次级（强制）

```bash
cd <repo> && pax-forge test   # 12 passed，0 failed
```

### 7.2 能力级（新能力必全过）

- 数据集自洽 `--selfcheck` PASS（无 TODO、id 唯一、gold 可契约推导）
- 变异体 100% 被杀（≥8 个）
- 快照正反用例全符合预期
- 能力分 ≥0.90（需真实调模型，未跑不得声称通过）

### 7.3 端到端验收场景

1. **0-1 项目**：一句话 → `pax-research`（调研/竞品/选型候选）→ `advisor` 评估 → `design` 定稿（含前端方向）→ `plan` → `execute` → `test` → `gate` → `deploy`。
2. **原型→PRD**：原型 HTML → `pax-prototype-to-prd`（生成+校验 PASS）→ `design` → `plan` → `execute`。
3. **PRD 变更**：新增导出功能 → 影响分析 → 提案 → 用户批准 → 传播 design/plan/test。
4. **生产发布**：`gate`（安全/合规/a11y/license，fail-closed）+ `deploy` + `monitor`/`rollback` 验证。

---

## 8. 落地推进建议

1. **先做 M0**：同步运行时到仓库 HEAD，确认 12/12。——这是当前性价比最高的一步，可立即执行。
2. 复核本裁定矩阵，确认 3 个新增/扩展的层级与优先级。
3. 设计 `prd` / `research` / `design.frontend` 段 schema（批量 minor bump）。
4. 按 M1→M3 拆 issue 实现，每个能力配真实评估资产。
5. M3 阶段收尾 §1.2 融合清单与骨架数据集。

---

## 9. 收官状态（完成后核对，2026-10-13）

v3 精简路线已全部落地并真跑评估，当前家族 **24 skill / v1.5.3**，仓库与安装运行时契约**均 12/12**。

| 项 | 状态 | 验证 |
|---|---|---|
| M0 运行时同步 | ✅ | 安装副本 19→24 skill，与仓库 HEAD 一致 |
| M1 `pax-research` | ✅ | 真跑 overall **97.1%** / valid 100%；not_verdict 弱项经 R4 措辞强化 67%→100% |
| M2 `pax-prototype-to-prd` | ✅ | 真跑 overall **100%** / valid 98.3%；传播门禁经 P4 对抗强化后通过（GATE PASS，60 判定） |
| M3 前端并入 design | ✅ | `pax-design` D9 前端阶段 + `design.frontend` 段 |
| 融合（§1.2） | ✅ | gate 接线 review/deploy、rollback 迁移可逆、incident→monitor/learn、cicd→deploy、refactor→review（既有）、memory→docs/learn、domain-pack→orchestrate、tech-stack→research、prd-val/change→prototype、design-sys→design |
| 接线（§1.3） | ✅ | evolve（learn 后触发 + 周期自审）、advisor（research/design） |
| 删除/放弃（§1.4） | ✅ | fullstack 放弃、8 骨架数据集删除 |
| 不做（§1.5） | ✅ | 移动端/K8s/MLOps 与日常任务均不入主干 |

**诚实说明（残留）**：
- research / prd 真跑用 `sensenova-6.8-flash-lite`（小模型）。对抗性变更指令（change-02："未批准仍要求直接传播"）在强化提示词后通过；若换更强模型，该档可更稳。
- 所有评估资产 selfcheck / 变异测试全绿；未引入依赖环或非法调用边。

---

**文档结束**
