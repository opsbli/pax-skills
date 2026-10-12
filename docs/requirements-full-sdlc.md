# pax-family 全流程能力补齐需求文档

**文档版本**：v2.0（重写版，取代 v1.0 草案）
**状态**：正式草案（待业务方裁定 §8 的 5 个开放问题）
**建议路径**：`docs/requirements-full-sdlc.md`
**目标读者**：pax-family 维护者、Skill 作者、`pax-orchestrate` 路由设计者、评估体系维护者
**基线仓库**：`opsbli/pax-skills` @ `main` = `d7e7b8a` → 本地含 `pax-design`（family **1.2.0**，21 skill）
**上游依据**：`docs/requirements-landing-review.md`（v1.1，实测裁定）

---

## 0. 本版与 v1.0 的差异（重要）

v1.0 草案提出 **18 个新 skill + 14 种新快照顶层段 + 30 个新意图标签**。
经探针实测（`evals/probe_requirements_feasibility.py`、`evals/probe_gap_claims.py`），
v1.0 存在两类问题，**本版已全部修正**：

| 问题 | 实测证据 | 本版处置 |
|---|---|---|
| v1 设计无法通过既有契约 | 14/14 新快照顶层段被 schema 拒绝；21 条非法层间调用边；8 个依赖环 | 全部改为复用既有段与既有层语义（§2） |
| v1 把「已有但未接线」误判为「缺失」 | 逐条回验后：仅 **7 项**是真缺口，**8 项**能力已存在，**3 项**不属于本仓库 | 需求规模由 18 收敛至 **7**（§4） |

**一句话结论**：v1 的问题不是「想太多」，而是**把「已存在」当成「不存在」导致重复建设**。

---

## 1. 背景与范围

### 1.1 现状

pax-family 以「快照为契约、状态机驱动、门禁 fail-closed」为核心，
已覆盖主干流程：`orchestrate → clarify → diagnose → plan → execute → review`，
并在 L1 挂载 `monitor / rollback / test / deploy / learn / analyze / design`，
L2 提供 `advisor / council`（只读顾问与盲审），L3 提供两个 worker，L4 提供
`verify / evolve / docs / init`。

主干 happy path 由 `pax-ops/versions.json#main_flow` 定义，不构成额外约束。

### 1.2 目标

- 补齐 **7 项真缺口**，且每项落地后**可评估**（有数据集 + 门禁阈值 + 变异测试）。
- **接线优先于新建**：先验证已存在但未接线的 `pax-evolve` 是否已满足部分需求。
- 保持 L0–L4 分层语义与「快照为契约」原则不变，**不新增顶层快照段**（除已落地的 `design`）。
- 家族 12 条契约全程保持通过。

### 1.3 非目标（明确不做）

- 不新增移动端 / K8s / MLOps 专项 skill——属下游领域包，详见 §4.3。
- 不重建外部路由评估体系——`evals/README.md` 已证明其基线（100%）无区分度，详见 §6.2。
- 不为跨阶段协作新建 L4 主动调度型 skill——L4 是叶子层，详见 §2.2。
- 不引入 §8 未裁定的口径前，不实现 `pax-memory`（L0 语义冲突，见 §2.3）。

---

## 2. 硬约束（设计前置条件，非建议）

本节是**不可违反**的契约事实。任何新需求若违反本节，设计阶段即应被拒绝。

### 2.1 快照顶层段封闭

`schemas/snapshot.schema.json` 顶层为 `additionalProperties: false`，
当前 19 个合法段名：`meta / goal / consensus / orchestration / symptom / diagnosis /
infrastructure / plan / contract / execution / review / quality / monitoring /
rollback / tests / deployment / learning / analysis / design`。

新增能力**必须复用既有段**，或走 minor bump 显式扩 schema。
`contracts.py` 的 `snapshot-field-conformance` 会扫描每个 skill 正文的
`snapshot.<段>.<字段>`，段名不存在即判违规——**绕过 schema 手工写 YAML 也过不了**。

### 2.2 L4 是叶子层，不可主动下探

`pax-ops/versions.json#compatibility_matrix` 只声明三行出边：

```
L0 → L1, L4
L1 → L1, L2, L3, L4
L2 → L3, L4
```

**L3 / L4 无出边**。`references/compatibility-matrix.md` 明确：「L4 是横切层，
只能被调用，不主动下探」。

> **常见误解**：把 L4 理解为「横切 = 到处插桩 = 可主动调度」。
> 本家族的 L4 语义是「横切 = 被 L1 在指定阶段调用」。两者不能共存。

**正确形态**：横切检查类能力（安全、合规、可访问性）应作为 **L1 的门禁阶段**，
由 L1 在评审/部署前调用，而非 L4 skill 回调 L1。

### 2.3 L0 是强制单一入口

`pax-orchestrate` 是唯一的 L0，且 `optional: false`。
`gate-refusal` 契约对 L0 有专门语义：门禁失败**必须拒绝启动**，
不得包装为「降级继续」。

**推论**：`optional: true` 的记忆层能力（如 `pax-memory`）**不宜占 L0**。

### 2.4 调用图必须无环

`no-cycles` 契约从每个 skill 正文抓取 `pax-*` 引用建调用图。

**约定**：跨阶段协作写成**数据流**而非调用边——只表达数据流时写阶段名
（「设计阶段」「评审阶段」），不要写 skill 名。

### 2.5 门禁 fail-closed 优先于「不阻塞任务」

`pax-orchestrate` 的 Execution Contract 是家族的门禁哲学基准：
**家族运行时装配不完整 = 硬拒绝启动**，不是可降级项。
新 skill 的冻结/校验逻辑必须与之一致，**不允许部分冻结**。

---

## 3. 能力缺口裁定（A / B / C 三档）

判据：是否存在**可执行结构**（判定函数 / 判定表 / 快照字段 / 脚本引用），而非词语出现。

> ⚠️ 探针仅作线索。`evals/probe_gap_claims.py` 脚本报「真缺口 14 / 已有 6」，
> 人工逐条回验后为 **7 / 8 / 3**。差异源于探针两类缺陷：
> 假阳性（「打包」=批量提问、`ipa` ⊂ `participants`）与
> 假阴性（漏判「闭环回退」已由 `pax-rollback` R1–R5 实现）。
> **断言必须回验原文**——这是探针输出不能直接引用的原因。

### 3.1 A 档：真缺口（需新建，7 项）

| # | 能力 | 现状实测 | 建议形态 |
|---|---|---|---|
| A1 | 安全扫描门禁（SAST/密钥/依赖漏洞） | 零 `SAST/DAST/gitleaks/trufflehog/CVE` 结构。`pax-orchestrate` 仅有 `security` 二级意图（升级 council），**无扫描能力** | **L1 门禁段**，由 review/deploy 调用（§2.2） |
| A2 | 合规治理（GDPR/SOC2/数据留存/同意管理） | 零 `GDPR/SOC2/HIPAA/data_retention` 结构 | 与 A1 合并为同一门禁段（共享检查项与证据格式） |
| A3 | 可访问性与国际化（WCAG/ARIA/i18n） | 零 `WCAG/ARIA/a11y/i18n` 结构 | 与 A1 合并（同为发布前静态检查） |
| A4 | 许可证合规 | 零 `license/GPL/AGPL` 结构 | 并入 A1 门禁段检查项 |
| A5 | 设计系统 / 设计令牌 | 零 `design_token/设计系统` 结构。`pax-init` 只扫技术栈（TS/Vite/Vue），不涉设计体系 | 独立 skill，**P1**（依赖前端体系先定型） |
| A6 | 代码级性能优化（N+1/慢查询/全表扫描） | 零 `N+1/慢查询/全表扫描` 结构 | **并入 `pax-diagnose` 检查项**，不建独立 skill |
| A7 | 周期性自审 | 零 `self_audit/自审/cron` 结构 | **先接线 `pax-evolve`**，实测不足再新建（§5） |

**净新建 skill 预估：A1–A4 合并为 1 个门禁段 + A5 一个 = 2 个新 skill**（非 7 个）。

### 3.2 B 档：已有结构（**不要新建**，接线或补断言）

| # | 需求文档的「缺口」 | 实测已有实现 | 处置 |
|---|---|---|---|
| B1 | 前置研究 / 竞品比对 / 技术选型 | `pax-advisor` A2 候选方案生成 + A3 证据加权评估（`composite_score` = 证据 0.4 / 风险 0.3 / 成本 0.3） | **接线**到 `pax-orchestrate` 入口；不改 skill |
| B2 | 可观测性设计（SLO/日志/指标/追踪） | **本轮已实现**：`pax-design` D6 `observability_plan`（logs/metrics/traces/slo）；`pax-monitor` 已有阈值告警 | 已闭环 |
| B3 | 数据库迁移安全 | `pax-plan.rollback_strategy` 四档（on_failure/on_alert/on_request/default）+ `derive_rollback_strategy()`；`pax-orchestrate` W2 不可逆性 3 档含「迁移有 down 脚本」 | 只需 `pax-test` 补 **up/down 实跑校验**，不建 skill |
| B4 | 代码重构流程 | `refactor` 已是既有 **6 类一级意图**之一，路由 `[clarify, plan, execute, review]` 完整 | 只需给 `pax-review` 加**行为等价性断言** |
| B5 | 事故响应与复盘 | `pax-monitor`（告警）+ `pax-learn`（经验沉淀）已覆盖；`pax-evolve` 是 OODA 闭环（含 A/B 验证门 + 回滚） | **接线 `pax-evolve`**，不建 `pax-incident` |
| B6 | 端到端闭环回退 | **已完整实现**：`pax-rollback` R1–R5（触发/选策略/执行/验证/报告）+ 前置门禁读 `plan.rollback_strategy`；`pax-deploy` D5 部署回滚；`pax-execute` 内环失败 → 回滚 | **无需任何改动** |
| B7 | 持久化项目记忆 | `pax-init` 已建 `.pax/` 目录 + `project-profile.json`；`pax-docs` 沉淀 CONTEXT/ADR；`pax-learn` 沉淀经验 | 边界待裁定（§8-Q3），**倾向增强 `pax-docs` 而非新建** |
| B8 | 对抗性 / 多标签评估 | `evals/` 已有对照实验（剥离禁令 100% → 71.1%）+ `build_control_subjects.py` + `add_holdout_cases.py --check` 锁定检测 | **已做过且有结论**，无需新建 |

### 3.3 C 档：不属于本仓库（移出范围，3 项）

| # | 能力 | 移出理由 |
|---|---|---|
| C1 | 移动端专项 | 与家族「编码流程契约」定位弱相关；应作下游领域包 |
| C2 | 云原生 K8s | 同上。零 `kubectl/helm` 结构，但文档自己列 P2 |
| C3 | MLOps / AI 工程 | 同上。零 MLOps 结构，文档自己列 P2 |

**建议**：转为独立的下游 skill 包，通过 `pax-worker-implement` 的领域适配接入，
不进入家族主干分层。

---

## 4. 需求条目（按七阶段归档）

按技能归档的七阶段法组织：总纲 / 需求 / 技术 / 设计 / 开发 / 测试 / 交付。
括号内为 §3 的裁定档位。

### 4.1 总纲（00）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| G-1 | 收敛路由意图标签：30 个新标签 → 6 个二级意图扩展 | — | P0 |
| G-2 | **接线 `pax-evolve`**（OODA 闭环骨架，当前无任何 skill 调用） | B5 | P0 |
| G-3 | 接线 `pax-advisor` 到更多 L1 入口（当前仅 analyze 升级路径） | B1 | P1 |
| G-4 | 消除 `pax-advisor` 的**影子 skill**：`references/full-body.md` 带完整 frontmatter（含 `name:`），按目录扫描的加载器会误认其为本体（见 §7D-1） | — | P0 |
| G-5 | 门禁段（L1）统一承载安全/合规/a11y/许可证四类检查 | A1–A4 | P1 |

### 4.2 需求（01）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| R-1 | 门禁段输出复用 `quality.verification_seals`（五态 + 证据 + 置信度），**不新增顶层段** | A1–A4 | P1 |
| R-2 | 门禁失败时 `deploy` 必须阻断（critical/high 不可部署） | A1 | P1 |
| R-3 | 记忆层边界裁定后再定实现（§8-Q3），**本轮不实现 `pax-memory`** | B7 | 阻塞 |

### 4.3 技术（02）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| T-1 | 迁移 up/down 实跑校验写 `tests.pie_check` | B3 | P1 |
| T-2 | 代码级性能优化并入 `pax-diagnose`（N+1 / 慢查询 / 全表扫描） | A6 | P1 |
| T-3 | 移动端 / K8s / MLOps 转下游领域包，**不进主干分层** | C1–C3 | P2 |

### 4.4 设计（04）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| D-1 | **设计系统 / 设计令牌**能力（`design_token` / 组件规范 / 视觉一致性） | A5 | P1 |
| D-2 | `pax-design` 已在 clarify↔plan 之间补位；**待真跑评估后定是否加强** | 已落地 | P0（验收） |

### 4.5 开发（05）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| V-1 | 给 `pax-review` 增加**行为等价性断言**（支撑重构类任务） | B4 | P1 |
| V-2 | 接线 `pax-monitor` → `pax-learn` 事故沉淀链 | B5 | P1 |

### 4.6 测试（06）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| T-1' | 新增能力**必须**配：数据集 + runner + 变异测试 | 全部 | P0（强制） |
| T-2' | 门槛按**契约确定性**分档（查表 0.95 / 自由文本 0.85），不从测量分布反推 | 全部 | P0（强制） |
| T-3' | 区分**能力分**与**输出健壮性**（`structure_failures` 单列） | 全部 | P0（强制） |
| T-4' | 新 skill 的 scorer 必须有 mutation test 证明（≥8 个变异体全杀） | 全部 | P0（强制） |

### 4.7 交付（07）

| ID | 需求 | 档位 | 优先级 |
|---|---|---|---|
| DL-1 | 端到端验收场景**前置**为验收用例来源（见 §5 M4 调整） | — | P0 |
| DL-2 | 每批次落地后跑全量契约（12/12）作为发布门禁 | — | P0（强制） |

---

## 5. 里程碑（按依赖顺序，阻断项优先）

### M0 — 接线先行（零新契约，最高性价比）

| 内容 | 依赖 | 说明 |
|---|---|---|
| G-2 接线 `pax-evolve` | 无 | 先验证 OODA 闭环是否已满足 A7 自审需求 |
| G-3 接线 `pax-advisor` | 无 | 消除「能力存在但入口不可达」 |
| G-4 修正 advisor description | G-3 | description 与实际状态一致性 |
| DL-2 全量契约 | — | 每步后 12/12 |

**出口判据**：拿真实任务验证接线后是否已覆盖 A7 / B1 需求。
若已覆盖 → **A7、B5 从需求清单移除**（避免重复建设）。

### M1 — 门禁段（唯一新建 skill，承载 A1–A4）

| 内容 | 依赖 |
|---|---|
| L1 门禁段：SAST / 密钥 / 依赖漏洞 / 许可证 / WCAG / i18n / GDPR | M0 |
| 输出复用 `quality.verification_seals` | §2.1 |
| 由 `review` / `deploy` 调用（**不放 L4**） | §2.2 |
| 配数据集 + runner + 变异测试 | §4.6 |

### M2 — 断言补强（不新建 skill）

| 内容 | 依赖 |
|---|---|
| T-1 迁移 up/down 实跑校验 | M1 |
| V-1 行为等价性断言 | M1 |
| T-2 性能优化并入 diagnose | M1 |
| D-1 设计系统 / 设计令牌 | M1 |

### M3 — 评估与验收

| 内容 | 依赖 |
|---|---|
| DL-1 端到端验收场景前置 | M1 |
| `pax-design` 真跑评估（需密钥） | — |
| 跨模型对照（`deepseek-v4-pro`） | — |

### 里程碑与 v1.0 的差异

| v1.0 | 本版 | 原因 |
|---|---|---|
| M0 = Schema + `pax-memory` | M0 = **接线**（零新契约） | 记忆层边界未定；接线成本更低、验证更快 |
| M1 = 7 个新 skill | M1 = **1 个门禁段**（承载 A1–A4） | 复用 `verification_seals` + L1 调用形态 |
| M2 = 8 项 | M2 = 断言补强（不新建） | B3/B4/B5 能力已存在 |
| M3 = mobile/k8s/mlops | M3 = 评估与验收 | C1–C3 移出范围 |
| M4 = 端到端验收 | **前置到 M1** | 验收场景应作用例来源，不是最后补 |

---

## 6. 非功能需求

| 类别 | 需求 | 验证方式 |
|---|---|---|
| 契约完整性 | 全程 12/12 契约通过 | `pax-forge test` |
| 分层合规 | 无非法调用边、无环 | `layer-call-legality` / `no-cycles` |
| 快照合规 | 不新增顶层段（除 `design`） | `snapshot-field-conformance` |
| 可评估 | 每个新能力有数据集 + 阈值 + 变异测试 | §4.6 强制项 |
| 门禁语义 | 门禁失败 fail-closed，不允许部分冻结 | `gate-refusal` + 人工评审 |
| 可维护 | 段所有权互斥（`consensus`/`plan`/`design` 各自独占） | 评审检查 |
| 向后兼容 | 不改 `pax-orchestrate` W1–W4 契约文本 | 内部路由基线（90.8%）应保持 |

### 6.2 明确不做：重建外部路由评估

v1.0 §5.21 建议新增对抗性与多标签路由评估。**现状已做过且有结论**：

- 外部路由基线 100%，但 `evals/README.md` 诚实记录：**该数字不含信息量**——
  20 个 skill 里绝大多数 description 自带「不要直接选择」禁令，
  模型做的是遵守禁令而非语义判断。对照组（剥离禁令）降至 **71.1%**，
  **28.9pp 是设计代价，不是能力**。
- `multi_exact` 指标已因**结构性无真值**被移除（入口单选时任何合法答案只能是单元素）。

**结论**：新增意图应测**内部路由**（`build_route` 触发条件），
复用 `run_internal_routing_eval.py` 模式，**不扩 catalog**。

---

## 7. 已知债项（本轮实测发现）

| ID | 债项 | 影响 | 处置 |
|---|---|---|---|
| D-1 | **影子 skill**：`skills/pax-advisor/references/full-body.md` 带**完整 frontmatter**（含 `name: pax-advisor`），且其 description 曾写「当前未接线」——而主 `SKILL.md` 已更新为「由 pax-analyze 委托调用」。`contracts.py:_iter_skill_dirs` 只扫 `skills/*/SKILL.md`，故契约层查不到它；但任何按目录递归扫描的 skill 加载器都可能把它误认成 `pax-advisor` 本体 | 双 description 冲突；可能被重复加载；契约盲区 | ~~M0 的 G-4~~ **已治**：剥离两个 `references/full-body.md` 的 frontmatter 与「未接线」旧文案 |
| D-2 | `scripts/run_skill_eval.py` 是**空桩**（`evaluate_skill` 全 TODO，不调模型） | 8 个「skeleton」数据集给人已可用的错觉 | 标注为 stub 或替换为真 runner |
| D-3 | 8 个单 skill 数据集全是 3 题 TODO 占位 | 「已建骨架」被误读为「已覆盖」 | 参照 `pax-design` 的 15 题真实数据集补齐 |
| D-4 | `pax-evolve` 曾是**骨架未接线**（SKILL.md:15 明写「无生产路由，正文已移至 references/full-body.md」） | OODA 闭环能力曾闲置 | ~~M0 的 G-2~~ **已治**：恢复正文至 SKILL.md、`status: active`，并由 `pax-orchestrate` 在 learn 之后登记触发 |

---

## 8. 待业务方裁定的开放问题

以下不适合由实现侧决定：

| # | 问题 | 影响面 | 建议默认值 |
|---|---|---|---|
| Q1 | L4 是否允许回调 L1？ | 决定 6 个横切 skill 形态 | **不允许**（按既有矩阵），横切改为由 L1 调用 |
| Q2 | 安全/a11y/合规/许可证是独立 skill 还是 L1 门禁段？ | 决定 M1 形态 | **合并为门禁段** |
| Q3 | `pax-memory` 与 `pax-docs`/`pax-init`/`pax-learn` 边界？ | 决定是否新增记忆层 skill | **先增强 `pax-docs`**（扩到 THINKING 面），零新增契约 |
| Q4 | 记忆文件与快照双写不一致时以谁为准？ | 决定 R-3 实现 | **快照为准**（快照是契约，记忆是派生视图） |
| Q5 | mobile/k8s/mlops 是否移出家族范围？ | 决定 C1–C3 | **移出**，转下游领域包 |

---

## 9. 验收标准

### 9.1 批次级（强制，每批次必过）

```bash
cd <repo> && python -m pax.forge test    # 或直接跑 contracts.run_all_contracts
# 期望：12/12 通过，0 violation
```

### 9.2 能力级（新能力必须全过）

| 检查项 | 门槛 | 说明 |
|---|---|---|
| 数据集自洽 | `--selfcheck` PASS | 无 TODO 占位、id 唯一、gold 可由契约推导 |
| scorer 有效性 | 变异体 **100% 被杀** | ≥8 个变异体，含自相矛盾结构 |
| 快照契约 | 正反用例全符合预期 | 正例接受、反例拒绝 |
| 能力分 | ≥0.90 | 需真实调用模型，**未跑不得声称通过** |

### 9.3 诚实性约束

- **未真跑的评估不得报数字**。参照家族既有纪律：
  `evals/README.md` 明确区分「真跑出来的」与「预期值」。
- **探针输出仅作线索**，结论必须回验原文（`probe_gap_claims.py` 已实测出现 14/6 vs 7/8/3 的偏差）。
- 交接时须列明**未做**事项与**未验证**风险。

---

## 10. 已落地部分（本轮）

| 项 | 内容 | 验证 |
|---|---|---|
| `pax-design`（L1） | D1 设计必要性 / D2 深度 / D3 候选 / D4 ADR / D5 接口与数据模型 / D6 服务边界 + SLO / D7 盲审 / D8 冻结（fail-closed） | 12/12 契约 |
| `snapshot.design` 段 | 顶层可选段，承接 ADR / 接口 / 数据模型 / 服务边界 / 可观测性 | 6 条正反用例 |
| 挂载点 | `clarify` 之后、`plan` 之前（**不可跳过 clarify**） | `layer-call-legality` |
| 评估资产 | 15 题数据集 + runner + 13/13 变异测试 + schema 校验 | `--selfcheck` / 变异测试全绿 |

**未完成**：`pax-design` 真实准确率**未测量**（需 `DEEPSEEK_API_KEY` + `openai`）。
本轮仅验证数据集自洽性、提示构造、scorer 有效性三项。

---

## 附录 A：索引

| 资源 | 路径 | 用途 |
|---|---|---|
| 本文档 | `docs/requirements-full-sdlc.md` | 需求主文档 |
| 落地评估（裁定依据） | `docs/requirements-landing-review.md` | v1.1 实测裁定 |
| 家族设计 | `docs/pax-family-design.md` | 分层与契约设计 |
| 契约执行器 | `src/pax/forge/contracts.py` | 12 条契约 |
| 快照 schema | `schemas/snapshot.schema.json` | 19 个合法顶层段 |
| 层矩阵（权威） | `pax-ops/versions.json#compatibility_matrix` | 合法调用方向 |
| 兼容性镜像 | `references/compatibility-matrix.md` | 人类可读（以 JSON 为准） |
| 评估总纲 | `evals/README.md` | 基线数字与可信度边界 |
| 契约可行性探针 | `evals/probe_requirements_feasibility.py` | 验证 v1 设计的违规点 |
| 缺口裁定探针 | `evals/probe_gap_claims.py` | A/B/C 档线索（**非结论**） |
| design 评估 runner | `evals/run_design_eval.py` | 真跑 / selfcheck / dry-run |
| design 变异测试 | `evals/mutation_test_design_eval.py` | scorer 有效性 |

## 附录 B：术语

| 术语 | 含义 |
|---|---|
| 快照 | `pax-snapshot`，跨 skill 传递的唯一契约载体 |
| 段所有权 | 每个顶层段由唯一 skill 独占写入，避免双写不一致 |
| fail-closed | 门禁失败时拒绝启动，不允许降级继续 |
| 接线 | 让已存在但无人调用的 skill 被路由引用 |
| A/B/C 档 | 真缺口 / 已有结构 / 移出范围（§3） |
| 探针 | 自动化取证脚本，输出是**线索**而非结论 |
| 变异测试 | 注入已知错误答案，验证 scorer 能判错 |