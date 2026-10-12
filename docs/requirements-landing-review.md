# pax-skills 全流程补齐：落地评估与精简建议

**文档版本**：v1.1（新增 §0「必要性裁定」，以远端实测数据取代推断）
**状态**：基于实测的落地评估（非需求复述）
**输入**：`docs/requirements-full-sdlc.md` 草案 v1.0
**基线仓库**：`https://github.com/opsbli/pax-skills` @ `main` = `d7e7b8a`（20 个 skill）
**方法**：以 `pax-ops/versions.json` / `schemas/*` / `src/pax/forge/contracts.py` 为唯一事实来源，
用探针脚本实测需求设计的契约可行性，而非依据文档描述推断。
**基线**：改动前家族 12/12 契约通过；本轮改动后仍 12/12。

---

## 0. 必要性裁定：「新增」到底新在哪

### 0.1 远端核对结果

| 项 | 值 |
|---|---|
| 远端 `main` HEAD | `d7e7b8a` "feat: doc_consult 引入只读分析落点并接线 pax-advisor" |
| 远端 skill 数 | **20**（`pax-analyze` … `pax-worker-research`） |
| 本地 HEAD | 同为 `d7e7b8a`，与远端**无差异** |
| 需求文档提议 | 18 个新 skill |
| 远端实际存在 | **0 个** |

**结论：需求文档描述的 18 个 skill 确实一个都不存在于 GitHub。**
但「不存在」≠「必要」——下一节逐条裁定必要性。

### 0.2 逐条必要性裁定

判据分三档：

- **A 真缺口**：无任何可执行结构 → 新建 skill 有必要
- **B 已有结构**：能力文本或等价实现已在家族内 → **不需要新 skill**，缺的是接线/触发条件
- **C 不建议**：能力真实但与家族定位无关 → 属于产品边界讨论，不是本仓库的缺口

复核方式：`python evals/probe_gap_claims.py`（结构性证据扫描）+ 人工核验上下文。

> ⚠️ **探针输出仅作线索，不可直接引用为结论**。脚本报「真缺口 14 / 已有结构 6」，
> 而人工核验后的裁定是「真缺口 7 / 已有结构 8 / 不建议 3」。
> 差异来自探针的两类已知缺陷：
> 1. **假阴性**（把已有当缺失）：`19 闭环回退` 实为**已完整实现**
>    （`pax-rollback` R1–R5 + `pax-plan.derive_rollback_strategy()` + `pax-deploy` D5），
>    但探针只搜 `fallback|回退路由` 这类词，搜不到 `rollback` 这套既有实现。
> 2. **假阳性**（词形误报）：v1 版关键词扫描中「打包」= 批量提问、
>    「orchestration」= 快照段名、「时间线」= pax-design 的排除项、
>    `ipa` ⊂ `participants`。
>
> **下表是人工逐条核验后的结论**，探针仅用于缩小范围。
> 这也印证了家族既有纪律：探针输出是**线索**，断言必须回验原文。

| # | 需求文档主张 | 裁定 | 实测依据 |
|---|---|---|---|
| 1 | 前置研究/竞品/选型 | **B** | `pax-advisor` A2 候选方案生成 + A3 证据加权评估（`composite_score` 0.4/0.3/0.3）；`pax-council` 盲审。缺的是**接线**（advisor 当前仅由 analyze 升级路径调用） |
| 2 | 独立设计/架构阶段 | **A** | 此前 `clarify` 直连 `plan`，中间无契约定稿环节 → **本轮已补 `pax-design`** |
| 3 | 前端样式/设计系统 | **A** | 全部 skill 无 `design_token`/`设计系统` 结构。`pax-init` 只扫技术栈（TS/Vite/Vue），不涉设计体系 |
| 4 | 安全专项门禁 | **A** | 无 SAST/DAST/密钥扫描/gitleaks/trufflehog/CVE 结构。`pax-orchestrate` 仅有 `security` 二级意图（升级 council），无扫描能力 |
| 5 | CI/CD 流水线生成 | **A** | 无 github actions/gitlab ci/jenkins 引用。`pax-deploy` D1–D5 是部署编排，非流水线生成 |
| 6 | 可观测性/性能 | **B** | **本轮 `pax-design` D6 已实现** `observability_plan`（logs/metrics/traces/SLO）；`pax-monitor` 已有阈值告警 |
| 7 | 数据库迁移安全 | **B** | `pax-plan.rollback_strategy` 四档（on_failure/on_alert/on_request/default）+ `derive_rollback_strategy()`；`pax-orchestrate` W2 不可逆性 3 档含「迁移有 down 脚本」。缺的是**up/down 实跑校验** |
| 8 | 可访问性/国际化 | **A** | 零 WCAG/ARIA/a11y/i18n 结构 |
| 9 | 事故响应/复盘 | **C** | 复盘本质是「监控事件 → 经验沉淀」，`pax-monitor` + `pax-learn` 已覆盖；`pax-evolve` 是 OODA 闭环但**未接线**。建议接线而非新建 |
| 10 | 依赖许可证合规 | **A** | 零 license/GPL/AGPL 检查结构 |
| 11 | 代码重构流程 | **B** | `pax-orchestrate` 已有 `refactor` 一级意图 + 路由 `[clarify, plan, execute, review]`；`pax-plan` 校验步骤回滚。缺的是**行为等价性断言** |
| 12 | 代码级性能优化 | **A** | 零 N+1/慢查询/全表扫描结构 |
| 13 | 合规治理 GDPR/SOC2 | **A** | 零 GDPR/SOC2/HIPAA/数据留存/同意管理结构 |
| 14 | 移动端 | **C** | 文档自己列为 P2；与家族「编码流程契约」定位弱相关 |
| 15 | 云原生 K8s | **C** | 零 kubectl/helm 结构，但文档列 P2；属产品边界，非本仓库缺口 |
| 16 | MLOps | **C** | 零结构，但文档列 P2；同上 |
| 17 | 持久化项目记忆 | **B** | `pax-init` 已建 `.pax/` 目录 + `project-profile.json`；`pax-docs` 沉淀 CONTEXT/ADR；`pax-learn` 沉淀经验。**记忆文件的职责边界需先裁定**（见 §5.3） |
| 18 | 周期性自审 | **A** | 零 self_audit/自审/cron 结构 |
| 19 | 端到端闭环回退 | **B（误判纠正）** | **能力已完整实现**：`pax-rollback` R1–R5（触发/选策略/执行/验证/报告）+ 前置门禁读 `plan.rollback_strategy`；`pax-plan.derive_rollback_strategy()`；`pax-deploy` D5 部署回滚；`pax-execute` 内环验证失败 → 回滚。**我的 v1 探针误判此项为缺口，实际是误报** |
| 20 | 对抗性/多标签评估 | **B** | `evals/` 已有对照实验（剥离禁令 100%→71.1%）+ `build_control_subjects.py` + 锁定检测。**已做过，且有结论** |

### 0.3 裁定汇总

| 档位 | 数量 | 处置 |
|---|---|---|
| **A 真缺口**（新建 skill 有必要） | **7** | 设计系统、SAST/密钥、CI/CD 生成、a11y/i18n、许可证、性能优化、合规、自审 |
| **B 已有结构**（**不要新建**） | **8** | 研究选型、可观测性、迁移安全、重构、记忆层、闭环回退、对抗性评估、事故复盘 |
| **C 不建议**（产品边界） | **3** | 移动端、K8s、MLOps |

**关键结论：18 个新 skill 里只有约 7 个是真缺口，另外 11 个要么能力已在
（只需接线/补断言），要么根本不属于这个仓库该解决的问题。**

### 0.4 「有必要吗」的直接回答

| 问法 | 答案 |
|---|---|
| 有必要新增吗？ | **有必要，但只需约 7 个，不是 18 个** |
| 有必要现在全做吗？ | **不必**。真缺口里还有优先级：A 档 7 项中，`自审`（零成本高杠杆）与 `性能优化`（可并入 diagnose）优先；`设计系统`/`a11y`/`许可证` 需等真实项目压力 |
| 需求文档该作废吗？ | **不该作废，该重排**。它的问题不是「想太多」，而是**把「已有但未接线」误判为「缺失」**，导致 11 项重复建设 |
| 我上一轮的落地对吗？ | **对且保守**。`pax-design` 属 A 档真缺口，且是 7 项里契约成本最低、杠杆最高的一个（复用既有段、不动 W1–W4） |

---

## 1. 结论先行（契约可行性）

需求文档提出新增 **18 个 skill** + **14 种新快照类型** + **30 个新意图标签**。
实测结论：**该设计无法直接落地**，会同时违反 3 类既有契约。本轮只落地其中
**契约可行、杠杆最高、复用度最高**的一个：`pax-design`（设计门禁）。

| 判定项 | 结论 | 证据 |
|---|---|---|
| 14 种新快照顶层段 | ❌ 全部被拒 | schema 顶层 `additionalProperties: false` |
| 6 个 L4 横切 skill 回调 L1 | ❌ 21 条非法边 | `compatibility_matrix` 未声明 L4 出边 |
| 文档声明的依赖图 | ❌ 8 个环 | `no-cycles` 契约 |
| `pax-memory` 置 L0 | ⚠️ 与强制入口语义冲突 | L0 为 `optional: false` 单一入口 |
| `pax-design`（本轮落地） | ✅ 契约通过 | 12/12 绿 + 6 条 schema 正反用例 |
| 其余新增 skill | ⏸️ 待口径裁定 | 见 §4 精简建议 |

复现命令（不调模型、不花钱）：

```bash
python evals/probe_requirements_feasibility.py   # 契约可行性探针
python evals/run_design_eval.py --selfcheck       # 数据集自洽性
python evals/mutation_test_design_eval.py         # scorer 有效性
python evals/validate_design_snapshot.py          # 快照段 schema 正反用例
```

---

## 2. 三个硬冲突（实测）

### 2.1 快照顶层段封闭——14/14 被拒

`schemas/snapshot.schema.json` 顶层是 `additionalProperties: false`，只认
`meta / goal / consensus / orchestration / symptom / diagnosis / infrastructure /
plan / contract / execution / review / quality / monitoring / rollback / tests /
deployment / learning / analysis` 这些名字。

需求文档第 6 章定义的 `research_snapshot` / `design_snapshot` / `security_snapshot` 等
**14 个顶层名全部被 schema 拒绝**。这不是风格问题，是 JSON Schema 层的硬拒绝。

同时 `contracts.py` 的 `snapshot-field-conformance` 会扫描每个 skill 正文里出现的
`snapshot.<段>.<字段>`，段名不存在即判违规——即使模型绕过 schema 手工写 YAML 也过不了契约。

**处置**：新增能力复用既有段，或显式扩 schema（本次为 `pax-design` 扩了 `design` 段，
属 minor bump）。**不要另起顶层命名。**

### 2.2 L4 是叶子层——21 条非法调用边

`pax-ops/versions.json#compatibility_matrix` 只声明了三行出边：

```
L0 → L1, L4      L1 → L1, L2, L3, L4      L2 → L3, L4
```

**L3 / L4 没有出边**。`references/compatibility-matrix.md:22` 写明：
「L4 是横切层，只能被调用，不主动下探」。

需求文档把 6 个 skill 放在 L4（security / db-migration / a11y-i18n / incident /
compliance / self-audit），同时要求它们**回调 L1**（如 `pax-security → pax-execute`、
`pax-self-audit → pax-plan`）。实测 **21 条边非法**。

这是**概念混淆**：需求文档把 L4 理解为「横切 = 到处插桩 = 可以主动调度」，
而本家族的 L4 语义是「横切 = 被 L1 在指定阶段调用」。两种理解不能共存。

**处置**：横切检查类能力的正确形态是——**由 L1 在门禁阶段调用**，
例如安全扫描挂在 `review` 与 `deploy` 之前，而不是让 L4 skill 自己去调 L1。

### 2.3 依赖图成环——8 个环

`no-cycles` 契约从每个 skill 正文里抓取 `pax-*` 引用建调用图。需求文档声明的依赖含：

```
design ↔ frontend-design        （互为依赖）
design ↔ design-system-extract
frontend-design ↔ a11y-i18n
security ↔ compliance
```

实测 8 个环。这类环在正文里必然出现——因为「A 消费 B 的产出」和「B 需要 A 的上下文」
在真实协作里都成立，但契约只认单向调用图。

**处置**：跨阶段协作写成**数据流**而非调用边。按 `compatibility-matrix.md:55` 的约定，
只表达数据流时写阶段名（「设计阶段」「评审阶段」），不要写 skill 名。

---

## 3. 本轮落地：`pax-design`

### 3.1 为什么选它

| 候选 | 契约可行性 | 复用度 | 杠杆 | 结论 |
|---|---|---|---|---|
| `pax-design` | ✅ L1，调用方向合法 | 复用 consensus/plan/ADR | 高：解锁「需求→计划」断层 | **本轮落地** |
| `pax-memory` | ⚠️ L0 语义冲突 | 与 pax-docs/pax-learn 边界不清 | 中 | 待裁定 |
| `pax-security` 等 6 个 L4 | ❌ 需改调用语义 | 可复用 review/deploy 门禁 | 高 | 改造后落地 |
| `pax-mobile`/`pax-k8s`/`pax-mlops` | ✅ 但无契约阻塞 | — | 低（P2） | 延后 |

`pax-design` 补的是家族当前最大的**结构性断层**：`clarify` 直接到 `plan`，
中间没有任何环节回答「接口契约定了吗、数据模型定了吗、这个不可逆决策的代价是什么」。
`pax-plan` 被迫在计划里临时发明架构，导致计划不可冻结。

### 3.2 交付物

| 文件 | 作用 | 验证方式 |
|---|---|---|
| `skills/pax-design/SKILL.md` | 设计门禁本体，D1–D8 | 12/12 契约通过 |
| `schemas/snapshot.schema.json` | 新增可选 `design` 段 | 6 条正反用例 |
| `schemas/pax-family.schema.yaml` | L1 成员登记 | `layer-membership` 契约 |
| `pax-ops/registry.json` / `versions.json` | 注册 + 版本 1.2.0 | `version-consistency` 契约 |
| `skills/pax-orchestrate/SKILL.md` | 挂载点：clarify 之后、plan 之前 | — |
| `evals/datasets/pax-design_v1.0.0.json` | 15 题，无占位 | `--selfcheck` PASS |
| `evals/run_design_eval.py` | 真实评估 runner | `--dry-run` 5011 字符提示 |
| `evals/mutation_test_design_eval.py` | scorer 有效性 | 13/13 变异体被杀 |

### 3.3 可维护性设计

- **单一事实来源**：设计产出只写 `snapshot.design` 一个段，不新起顶层命名。
- **段所有权互斥**：`consensus` 由 `clarify` 独占，`plan` 由 `plan` 独占，
  `design` 由本 skill 独占。三者不重叠，避免双写不一致。
- **冻结门禁 fail-closed**：`freeze_design()` 自检任一项缺失即 `blocked`，
  **不允许部分冻结**（对齐 `pax-orchestrate` 的门禁哲学）。
- **契约长度受控**：4572 字符，与家族既有 skill 同量级，可被整体读入不需切片。
- **不改既有行为**：`pax-design` 是 `optional: true`，不挂载时家族行为与改动前完全一致。

### 3.4 可评估性设计

沿用家族既有的**内部路由评估**方法论（`run_internal_routing_eval.py` 的模式）：

| 设计要点 | 做法 |
|---|---|
| 不测 stub 测真身 | 系统提示 = SKILL.md 的 D1–D3/D8 原文，不注入契约外澄清 |
| 门槛按契约确定性分档 | 查表类 0.95，自由文本类 0.85；不从测量分布反推 |
| 区分能力分与健壮性 | `structure_failures` 单列，不把 JSON 解析失败算成设计判断错 |
| gold 可从契约推导 | 每题 gold 均能由 prompt + SKILL.md 唯一推出 |
| scorer 必须有 teeth | 13 个变异体全部被杀，含 4 个自相矛盾结构 |

**诚实声明**：`run_design_eval.py` 的**真实准确率尚未测量**——需要
`DEEPSEEK_API_KEY` 与 `openai` 包。本轮只验证了数据集自洽性、提示构造正确性、
scorer 有效性三项，**未产出能力分数字**。任何「pax-design 准确率 X%」的说法
在真跑之前都不成立。这与家族既有记录对 100% 数字的处理方式一致
（`evals/README.md` 明确区分「真跑出来的」与「预期值」）。

---

## 4. 精简与优化建议

### 4.1 18 个 skill → 建议收敛到 4 个

> 本节已按 §0.2 的必要性裁定重写。上一版基于「文档说要新增」的推定，
> 误把 6 项已有能力当成缺失；现以实测为准。

| 原提议 | §0 裁定 | 建议 | 理由（实测依据） |
|---|---|---|---|
| `pax-security`（L4） | A 真缺口 | **新增 L1 门禁段，不放 L4** | 无任何 SAST/密钥扫描结构，能力确缺；但 L4 不能回调 L1，须由 L1 在门禁阶段调用 |
| `pax-a11y-i18n`（L4） | A 真缺口 | 合并进上述门禁段 | 零 WCAG/ARIA 结构，能力确缺；与安全同为「发布前静态检查」，拆开只增路由复杂度 |
| `pax-db-migration`（L4） | **B 已有** | **不新增**，增强 `pax-test` | `pax-plan.rollback_strategy` 四档 + `derive_rollback_strategy()` 已实现迁移回滚规划；只缺 up/down 实跑校验 |
| `pax-incident`（L4） | **C/B** | **不新增**，接线 `pax-monitor` → `pax-learn` | 复盘 = 监控事件 → 经验沉淀，两段都在；`pax-evolve`（OODA 闭环）已存在但**未接线** |
| `pax-compliance`（L4） | A 真缺口 | 合并进安全门禁段 | 零 GDPR/SOC2/数据留存结构；与安全共享检查项与证据格式 |
| `pax-refactor`（L1） | **B 已有** | **不新增**，给 `pax-review` 加行为等价性断言 | `refactor` 已是既有 6 类一级意图，路由 `[clarify, plan, execute, review]` 完整 |
| `pax-auto-research`（L1） | **B 已有** | **不新增**，接线 `pax-advisor` | A2 候选生成 + A3 证据加权评估（composite_score）已在；当前只由 analyze 升级路径调用，未接到入口 |
| `pax-design`（L1） | A 真缺口 | ✅ **本轮已落地** | clarify→plan 断层 |
| `pax-self-audit`（L4） | A 真缺口 | 新增，但**接线优先于新建** | 零自审结构；`pax-evolve` 未接线，可先接线验证是否已满足需求 |
| `pax-design-system-extract`（L2） | A 真缺口 | 延后到 P1 | 真缺，但依赖前端体系先定型，否则反复返工 |
| `pax-mobile` / `pax-k8s` / `pax-mlops` | **C 不建议** | **移出本仓库范围** | 与家族「编码流程契约」定位弱相关；应作为下游领域包而非家族 skill |
| `pax-orchestrate` 30 个新意图标签 | — | **收敛为 6 个二级意图扩展** | 30 个标签会让外部路由准确率不可维护 |

**净效果**：18 个新 skill → **本轮 1 个 + 后续约 4 个**（安全/a11y/合规合并门禁段、
设计系统提取、自审、许可证/性能并入 diagnose），**4 个降级为接线**（research→advisor、
refactor、incident→monitor/learn、evolve），**3 个移出范围**（mobile/k8s/mlops）。
路由表复杂度下降，契约风险归零。

### 4.2 快照设计：14 → 1（分批）

建议把 14 种新顶层段压到 **3 个**：

| 段 | 承载 | 替代原提案 |
|---|---|---|
| `design`（本轮已落地） | ADR / 接口 / 数据模型 / 服务边界 / 可观测性 | `design_snapshot` + `frontend_design_snapshot` + `tech_stack_snapshot` |
| 复用 `quality.verification_seals` | 安全 / a11y / 合规检查结果 | `security_snapshot` + `a11y_i18n_snapshot` + `compliance_snapshot` |
| 复用 `analysis` | 事故复盘 | `incident_snapshot` |
| **不新增** | 迁移安全 | `migration_snapshot` —— 复用 `plan.rollback_strategy` 四档；实跑校验写 `tests.pie_check` |

理由：`verification_seals` 本就是「五态 + 证据 + 置信度」的通用容器，
安全扫描结果天然就是这个形状；硬造新段只会让 schema 无限膨胀。

### 4.3 评估体系：别新增 runner

需求文档 §5.21 建议新增对抗性测试与多标签路由评估。**现状已经做过，且有结论**：

- 外部路由基线 100%，但 `evals/README.md` 已诚实记录：**这个数字不含信息量**——
  18 个 skill 里 17 个的 description 自带「不要直接选择」禁令，模型做的是遵守禁令而非语义判断。
  对照组（剥离禁令）降到 71.1%，**28.9pp 差距是设计代价，不是能力**。
- `multi_exact` 指标已因**结构性无真值**被移除（入口单选时任何合法答案只能是单元素）。

**建议**：不要为 30 个新意图标签重建外部路由评估。新增意图应该测的是
**内部路由**（`build_route` 的触发条件），复用 `run_internal_routing_eval.py` 的模式，
而不是扩 catalog——后者已被证明测不出区分度。

### 4.4 记忆层：先厘清边界再动手

`pax-memory` 有三个未解问题，任何一个不解决都会做出一个错的东西：

1. **L0 语义冲突**：L0 是 `optional: false` 的强制单一入口，
   `gate-refusal` 契约对 L0 有专门语义。记忆层是可选能力，不宜占 L0。
2. **与既有 skill 边界**：`pax-docs`（沉淀 ADR/CONTEXT）+ `pax-init`（项目画像）
   + `pax-learn`（经验沉淀）已覆盖持久化。`pax-memory` 的五文件
   （`PRODUCT/MILESTONES/TASKS/THINKING/DESIGN`）与三者职责**高度重叠**。
3. **双写一致性**：快照是任务级，记忆是项目级，两者同步失败时以谁为准？

**建议**：**先做增强，后做新 skill**——把 `pax-docs` 的沉淀面从 CONTEXT/ADR 扩到
`THINKING.md`（架构决策与踩坑），复用既有 `snapshot.quality.evolution_entries` 做版本化。
这样零新增契约就能拿到 80% 的记忆层价值。

### 4.5 里程碑重排建议

按 §0.2 裁定结果重排（A=真缺口，B=接线，C=移出范围）：

| 原里程碑 | 裁定构成 | 建议 |
|---|---|---|
| M0（Schema + pax-memory） | B 记忆层 | 拆为 **M0a: pax-design 落地**（已完成）+ **M0b: 接线 `pax-advisor` / `pax-evolve`**（零新契约，先验证是否已够用）+ M0c 记忆层口径裁定 |
| M1（7 个新 skill） | A×3 + B×2 | 收敛为 **1 个 L1 门禁检查段**（security+a11y+compliance 合并）+ 设计系统提取 + 自审 |
| M2（8 项） | A 性能/许可证 + B 迁移/重构 | 性能优化与许可证并入 `pax-diagnose` 检查项；迁移/重构**只补断言不建 skill** |
| M3（P2 三项） | **C×3** | **移出本仓库**，转为下游领域包 |
| M4（端到端验收） | — | **提前到 M0b 之后**——先用验收场景验证「接线」是否已满足需求，再决定要不要新建 |

**关键顺序调整（两条）**：

1. **接线先于新建**。`pax-advisor`（研究/选型）与 `pax-evolve`（OODA 闭环）
   都已实现但未接线。需求文档中 4 个「新增」项（research / incident / 自审的 OODA 部分）
   可能接线即可满足——**先接线、拿真实任务验证，再决定是否新建**。
2. **验收场景前置**。原文档把端到端验收放在 M4，但 §8 的 8 个验收场景
   本轮已暴露缺口：只列了 `frontend_design` 意图，却没有「设计系统检测」的落点。
   验收场景是验收用例的来源，应前置到设计阶段而非最后补。

---

## 5. 待业务方裁定的开放问题

以下问题**不适合由实现侧决定**，需要口径确认：

| # | 问题 | 影响面 | 本轮处理 |
|---|---|---|---|
| 1 | L4 是否允许回调 L1？ | 决定 6 个横切 skill 的形态 | 按既有契约（不允许）执行，横切改为由 L1 调用 |
| 2 | 安全/a11y/合规是独立 skill 还是 `pax-review` 的门禁段？ | 决定后续 3~7 个 skill 是否存在 | 倾向合并为门禁段 |
| 3 | `pax-memory` 与 `pax-docs`/`pax-init`/`pax-learn` 的边界？ | 决定记忆层是否值得新增 skill | 倾向先增强 `pax-docs` |
| 4 | `refactor` 一级意图是否需要独立 skill？ | 决定 `pax-refactor` 是否存在 | 倾向不新增 |
| 5 | 外部路由 catalog 是否随新 skill 扩容？ | 决定评估成本 | 倾向不扩（已证明无区分度） |

---

## 6. 本轮未做的事（诚实边界）

- **未测量 `pax-design` 真实准确率**——需 API key，本轮只验证数据集/提示/scorer 三项。
- **未运行外部路由评估**——需 skillEval 工具链与密钥。
- **未实现 §4 建议的其余 3 个 skill**——等 §5 口径裁定。
- **未改 `pax-orchestrate` 的 W1–W4 契约文本**——只新增了可选扩展 skill 表；
  意图分类与风险评分逻辑**一字未动**，故内部路由基线（90.8%）不受影响。
- **未验证跨模型表现**——只对照了契约层可行性，未做 `deepseek-v4-pro` 对照。