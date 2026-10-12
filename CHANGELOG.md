# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added（M0–M3 工作流补齐，基于 `docs/requirements-full-sdlc.md`）
- **`pax-gate`（L1，门禁段 skill，M1）**：承载 A1–A4 四类发布前静态检查——安全（SAST/密钥/依赖漏洞）、
  合规（GDPR/SOC2/数据留存/同意管理）、可访问性与国际化（WCAG/ARIA/a11y/i18n）、许可证（GPL/AGPL）。
  输出复用 `snapshot.quality.verification_seals`（不新增顶层段）；**fail-closed**：critical/high 必阻断部署。
  由评审/部署阶段通过五态印章消费（不放 L4）。配套真实可执行评估资产：15 题数据集 + `run_gate_eval.py`
  + 11 变异体 + 5 结构用例全杀。
- **接线 `pax-evolve`（L4，M0）**：恢复 `references/full-body.md` 正文至 `SKILL.md`、`status` active，
  由 orchestrate 在学习阶段之后登记触发（OODA 闭环：经验条目 + A/B 验证门 + 回滚）。
- **清理影子文档（G-4/D-1，M0）**：剥离 `pax-advisor` 与 `pax-evolve` 的 `references/full-body.md` 的
  frontmatter，避免目录扫描加载器误认成本体。
- **断言补强（M2，不新建 skill）**：`pax-review` R2.6 重构行为等价性断言；`pax-diagnose` D2.6
  代码级性能诊断（N+1/慢查询/重复计算）；`pax-test` T1.6 迁移 up/down 实跑校验；`pax-monitor`
  事故沉淀链（critical/回滚信号 → 学习阶段）。

### Changed（M3 评估）
- `pax-design` 与 `pax-gate` 能力分**真实测得**（`sensenova-6.8-flash-lite`，45 次/项）：
  design overall 95.7%、gate overall 98.3%；两处契约/数据集边界（design `freeze_gate`、gate `compliance`）
  如实记录待裁定。

### Removed
- `pax-forge test --skill`：自引入起就是**死选项**（`cli.py` 的 test 分支只调
  `run_all_contracts(root)`，从不读 `args.skill`；带与不带输出完全相同）。
  它的语义对 11 条契约中的 4 条家族级契约（`layer-membership` /
  `compatibility-matrix-consistency` / `declared-checks-coverage` / `no-cycles`）
  无法定义——保留一个半生效的过滤器只会给出「我查过某个 skill 了」的假信心。
  需要按 skill 排查时，直接看 `pax-forge test` 输出里带 skill 名的那一行。
- **删除 8 个骨架评估数据集**（`pax-deploy/execute/monitor/plan/review/rollback/test/verify` 的
  `_v0.1.0.json`，各 3 题 + TODO 占位）：它们会误报「这 8 个主线环节已被评估覆盖」。
  删除而非补齐，避免承载误导性占位；后续如需评估这些环节，按 `pax-design`/`pax-research` 的真实数据集模式补齐。

### Added
- **融合接线（v3 §1.2 收尾）**：
  - `pax-design` D7：`medium` 风险、无需全量盲审时的方案权衡，委托 `pax-advisor`
    （证据加权，L1→L2 合法）；盲审仍由 `pax-council` 承担，两者不互替。
  - `pax-deploy` D2.5：环境差异检测（目标 vs 部署源，对应 `deployment` 意图）+ CI/CD
    流水线一致性校验 + 回滚联动（与 `pax-rollback` 数据流）；不新增独立 skill。
  - 注：`pax-monitor` 事故沉淀链（incident→学习阶段）已在既有提交落地，无需重复。
  家族版本 1.5.1 → 1.5.2（skill 正文增强 → patch）。已同步安装运行时。
- **`pax-design` 前端产出阶段（D9，并入设计，不新增 skill）**：承接前端视觉产出——F1 设计系统检测
  （内部步骤）/ F2 风格一致性 / F3 反 AI 套路规避 / F4 0-1 视觉方向 / F5 视觉验证。
  `snapshot.design` 段新增可选 `frontend` 子对象
  （design_system_ref/visual_direction/components/pages/anti_ai/visual_verification）。
  纯后端设计可跳过（记 skip_reason）。家族版本 1.5.0 → 1.5.1（可选字段扩展 → patch）。
  已同步安装运行时。
- **新增 `pax-prototype-to-prd`（L1，需求工程上游）**：从原型（HTML/截图/Figma/Axure 导出）
  生成结构化 PRD，四阶段串一个 skill：原型解析 → PRD 生成（每条功能配 **EARS** 验收标准）→
  质量门禁（缺必备章节 / 验收标准非 EARS → `FAIL` 并 **fail-closed** 阻断进入下游）→ 变更管理
  （影响分析 → 提案 → 用户批准 → 传播，**未批准不传播**）。挂载点为 `clarify` 阶段内或之前
  （`orchestration.annotations.prototype_to_prd == true`）。快照新增顶层可选段 `prd`
  （source/pages/features/functional_requirements/acceptance_criteria/data_dictionary/scope/
  verification/change）。家族版本 1.4.0 → 1.5.0（新增 skill + 新增顶层可选段 → minor）。
  已同步安装运行时（24 skill）。配套可评估资产（**均为真实可执行，非占位**）：
  - `evals/datasets/pax-prototype-to-prd_v1.0.0.json`：12 题（prd_required 4 / ears_gate 2 /
    fail_closed 2 / change_pending 3 / scope_coverage 1），无 TODO 占位。
  - `evals/run_prd_eval.py`：真实调模型 runner，含 `--selfcheck` / `--dry-run` / `--rescore`。
  - `evals/mutation_test_prd_eval.py`：15 个变异体全部被杀，证明 scorer 有 teeth。

- **新增 `pax-research`（L1，开发前研究阶段）**：承接需求调研 / 竞品比对 / 技术选型的
  **信息采集**，产出可交接候选集（`snapshot.research`），**只出候选、不做裁决**（符合
  「AI 产出为候选」契约）；选型评估交 advisor、高风险交 council（L1→L2 合法），方案定稿
  交设计/规划阶段（数据流，不跨阶段）。挂载点为 `clarify` 之前或并行（
  `orchestration.annotations.research_required == true` 时）。快照新增顶层可选段
  `research`（question/scope/sources/findings/competitors/alternatives/
  recommendation_candidate/confidence/open_questions/read_only）。家族版本
  1.3.0 → 1.4.0（新增 skill + 新增顶层可选段 → minor）。已同步安装运行时（23 skill）。
  配套可评估资产（**均为真实可执行，非占位**）：
  - `evals/datasets/pax-research_v1.0.0.json`：12 题（research_required 5 / candidate_sufficiency 2 /
    not_verdict 2 / source_credibility 2 / read_only 1），无 TODO 占位。
  - `evals/run_research_eval.py`：真实调模型的评估 runner，含 `--selfcheck` / `--dry-run` /
    `--rescore`；门槛按契约确定性分档。
  - `evals/mutation_test_research_eval.py`：14 个变异体全部被杀，证明 scorer 有 teeth。

- **新增 `pax-design`（L1，设计门禁）**：承接已澄清需求，产出可冻结设计契约
  （ADR / 接口契约 / 数据模型 / 服务边界 / 可观测性设计），供 `pax-plan` 作为约束消费。
  挂载点为 `clarify` 之后、`plan` 之前（**不可跳过 clarify 直接设计**）。
  快照新增顶层可选段 `design`（design_required/skip_reason/depth/candidates/adrs/
  api_contracts/data_models/service_boundaries/observability_plan/security_considerations/
  review/open_questions/status/frozen_at）。
  家族版本 1.1.0 → 1.2.0（新增 skill + 新增顶层可选字段 → minor）。
  配套可评估资产（**均为真实可执行，非占位**）：
  - `evals/datasets/pax-design_v1.0.0.json`：15 题（design_required 8 / design_depth 4 /
    candidate_sufficiency 2 / freeze_gate 1），无 TODO 占位。
  - `evals/run_design_eval.py`：真实调模型的评估 runner，含 `--selfcheck` / `--dry-run` /
    `--rescore`；门槛按契约确定性分档而非从测量分布反推。
  - `evals/mutation_test_design_eval.py`：13 个变异体全部被杀，证明 scorer 有 teeth。
  - `evals/validate_design_snapshot.py`：6 条正反用例验证 `design` 段 schema 约束有效。
  - `evals/probe_requirements_feasibility.py`：需求文档设计的契约可行性探针（见下）。
- **新增 `pax-analyze`（L1，只读分析/调研执行落点）**：doc_consult 路由的正式执行阶段，
  承接代码/数据链路溯源、事实调研、行为解释，产出带证据链的分析结论。
  `doc_consult` 路由从 `[clarify, docs]` 改为 `[clarify, analyze]`，沉淀可选（`analysis_optional_docs`）。
  快照新增顶层可选段 `analysis`（findings/conclusion/confidence/open_questions/read_only）。
  家族版本 1.0.0 → 1.1.0（新增 skill + 新增顶层可选字段 → minor）。

### Changed
- **需求文档的 18 个新 skill 设计经探针验证与既有契约冲突**，本轮只落地其中
  契约可行且杠杆最高的一个（`pax-design`），其余待口径裁定后再增补。实测结论：
  - **14 个 `*_snapshot` 顶层段全部被 `snapshot.schema.json` 拒绝**（`additionalProperties: false`）。
    新增能力必须复用既有段或显式扩 schema，不能另起顶层命名。
  - **L4 是「只被调用、不主动下探」的横切层**（`compatibility_matrix` 未声明 L4 出边）。
    需求文档把 `pax-security` / `pax-db-migration` / `pax-a11y-i18n` / `pax-incident` /
    `pax-compliance` / `pax-self-audit` 放在 L4 并要求它们回调 L1，会产生 **21 条非法调用边**。
    横切检查的正确形态是**由 L1 在指定阶段调用**，而非 L4 向下回调。
  - 文档声明的依赖图含 **8 个环**（design↔frontend-design、security↔compliance 等），
    会直接触发 `no-cycles` 契约失败。
  - `pax-memory` 声明为 L0，但 L0 是 `optional: false` 的强制单一入口
    （`gate-refusal` 契约对 L0 有额外语义要求），不宜承载可选的记忆层能力。
- `doc_consult` 不再默认走 `pax-docs` 强制沉淀；仅当用户需要留档时才追加。
- `pax-advisor` 由 `skeleton` 恢复为 `active`，并接线到 `pax-analyze` 升级路径
  （分析中遇决策/权衡/架构型追问时委托其提供只读建议）；version 仍 1.0.0，不新增快照字段。
  （待填）

## [1.0.0] - 2026-10-05

### Breaking

**家族版本 0.2.0 → 1.0.0：快照格式升至 2.0，`schemas/snapshot.schema.json` 必填字段变更。**

按 `references/compatibility-matrix.md` 的规则，修改快照必填字段即触发 major bump。变更清单：

- `orchestration` 新增必填 `intent` / `risk` / `annotations` 三段（此前 skill 已在读写，但 schema 未登记）
- `execution` 新增必填 `status`（`completed|failed|paused`），并新增 `id` / `completed_at` / `commits`
- 新增六个顶层段：`monitoring` / `rollback` / `tests` / `deployment` / `learning` / `infrastructure`
- `consensus` 新增 `settled_at`；`plan` 新增 `id` / `frozen_at` / `frozen_by` / `rollback_strategy`
- `review` 新增 `verification_results` / `deviations_check` / `stamp_check` / `reviewed_at` / `reviewed_by`
- `meta.version` 1.0 → 2.0
- `quality.verification_seals` 成为 verify 印章的唯一落点（此前 skill 私造顶层 `verify_stamp`）
- `compatibility_matrix` 由「5 条 skill 级主干边」改为**层间全量方向**；`contracts._allowed_calls()` 改为读取它，
  不再各维护一份（分层矩阵与 19 个 skill 逐对展开等价，但可维护）
- `schemas/pax-family.schema.yaml`：`layers` 补齐（L1 +5、L4 +1），新增 `non_runtime_layers: [meta]`，
  `required_frontmatter` 加入 `optional`，新增 `declared_checks` 声明

### Added
- `contracts.py` 新增 4 条机械约束，堵住此前无法被 CI 发现的静默漂移：
  - `snapshot-field-conformance`：skill 提到的 `snapshot.<段>[.<字段>]` 必须存在于 snapshot schema
  - `layer-membership`：`schema.layers` 枚举必须与 `registry.json` 一致（双向）
  - `compatibility-matrix-consistency`：矩阵层名合法、不指向非运行时层、`main_flow` 每步方向合法
  - `declared-checks-coverage`：`schema.contracts.declared_checks` 必须与实现的契约名集合一致
- `loader.resolve_family_root()` 与全部 loader 的 `family_root` 参数：契约与生成器改为读「目标家族」
  而非工具安装位置，`pax-forge init <dir>` 后在新目录执行 `new`/`validate`/`test` 才真正自包含
- `pax-forge new --use-case`，修复 `L1.tmpl` 的 `use_case` 死变量（此前生成的 L1 skill 描述恒为「处理该类任务」）
- `validator` 新增 `layer` 取值合法性校验与 `optional` / `requires_snapshot` 布尔类型校验
- `pax-init` 新增「无变化不落盘」门槛（规则 8）与 W5/W6 的 `skip_reason: no_change` 行
- `pax-plan` 新增 `derive_rollback_strategy()`；`pax-execute` 新增 `commits` 收集与 fix 模式 diagnosis 门禁
- `pax-orchestrate` W2 补 `risk.forced_escalation` 写入义务，补 `performance`/`integration`/`deployment` 三个二级意图标注

### Changed
- `references/compatibility-matrix.md` 重写为层间全量矩阵 + `main_flow`，并写明「正文出现 `pax-<name>`
  即视为调用边，只表达数据流向时写阶段名」的约定（避免 `no-cycles` 产生假环）
- `docs/pax-family-design.md` 5.1/5.2 快照结构与不变式同步到 2.0
- `README.md` 版本一节改为明确三个独立版本维度（家族 / 工具包 / 快照格式）
- `registry.json` 的 `registered_at` 统一为 UTC `Z` 格式

### Fixed
- **README 路由评估段引用了 `evals/README.md` 已明确撤回的 2026-09-30 数字**
  （81.1% / 97.2% / 100% / 0%），并指向不存在的 `tools/skillEval/...`、把关键词桩测试说成「内部路由测试」、
  把从未调用模型的 `real_scenario_trial.md` 说成「真实场景试跑」。该段已改为只给入口与归档日期
- **SkillOpt 训练的表述失实**：`clarify_v2` / `diagnose_v2` 的 `training_summary.json` 均为 `dry_run: true`，
  且奖励函数是「技能文档命中关键词的比例」（`train_pax_offline.py`，纯子串计数，不调用模型），
  `initial=0.0 → final=1.0` 是构造必然。已改为如实描述
- `pax-learn` 门禁读 `snapshot.review.status`（schema 无此字段）→ `review.verdict in (pass, partial)`
- `pax-verify` 的顶层 `verify_stamp` → 追加到 `quality.verification_seals`；
  `pax-review` 的 `check_stamp` / `determine_verdict` 改为读该数组末位
- `pax-rollback` 门禁依赖 `plan.rollback_strategy`、读取 `execution.commits`，而上游从不产出 → 已在 `pax-plan` / `pax-execute` 补上产出
- `pax-execute` 的 fix 模式约束此前无门禁 → `E1 check_gate` 补 `diagnosis.status == settled` 与 `root_cause.statement` 非空校验
- `pax-orchestrate` 的 `is_cross_repo` 用裸子串匹配（`"web"` 命中 `webhook`、`"api"` 命中 `rapid`）
  且硬编码客户仓库名 `ops-monitor` / `ops-pilot-web` → 改为词边界匹配并移除硬编码
- `pax-orchestrate` 的 `init_snapshot` 引用不存在的 `risk.precision` → `precision_from_total(risk.total)`
- `pax-orchestrate` 的「完整工作流示例」图与扩展 skill 表的 `monitor` 触发时机矛盾 → 改为与表一致
- `pax-advisor` / `pax-worker-implement` / `pax-evolve` 的 description 声称被 pax-orchestrate 调用，
  但全仓 0 个其他 skill 引用它们 → 改为如实标注「当前未接线」

## [0.2.0] - 2026-09-30
- `pax-init`（L4，可选，`requires_snapshot: false`）：项目接入 Skill，由用户直接调用而非编排路由（家族成员 18 → 19）。扫描目标项目技术栈（Java/Maven、Spring Boot、RuoYi、TS/Vite/Vue/React、Go、Python、Docker、CI/CD 等），发现项目自有规范文档并只登记指针，生成 `AGENTS.md`（人可读）与 `.pax/project-profile.json`（机器可读），并幂等创建 `.pax/` 产物目录。附带 `references/tech-stack-detection.md`（检测规则单一事实源）、`references/project-profile-spec.md`（profile 字段规格）、`templates/AGENTS.md.tmpl`、`templates/project-profile.json.tmpl` 与确定性扫描器 `scripts/scan_project.py`。
- `tests/test_pax_init_scan.py`：7 项测试覆盖扫描器诚实性契约——命中即带证据文件、未命中一律「未检测到」、包管理器优先级（pnpm > yarn > npm > 未检测到）、多项目前后端合并与构建命令回退、规范文档只登记指针不复制原文、扫描幂等且只读、路径不存在时拒绝执行。
- `pax-monitor` / `pax-rollback` / `pax-test` / `pax-deploy` / `pax-learn`：将家族从 13 个扩展到 18 个（`pax-ops/versions.json` 已同步）。
- `evals/skillopt/train_pax_offline.py`：SkillOpt 链路冒烟脚本（rollout → reflect → aggregate → select → update → evaluate）。
  ⚠️ 奖励函数是「技能文档命中关键词的比例」（纯子串计数，不调用模型、不执行任务），
  因此 `final_reward=1.0` 只说明关键词已粘入文档，**不是能力提升的证据**；`gates.all_actions_covered` 同义。
- SkillOpt 训练集 v2：`pax_clarify_train_v2.jsonl` / `pax_clarify_eval_v2.jsonl`（14 + 7 例）+ `pax_diagnose_train_v2.jsonl` / `pax_diagnose_eval_v2.jsonl`（10 + 5 例）。
- 首次跑通 pax-clarify 和 pax-diagnose 的 SkillOpt 链路（`dry_run: true` 冒烟）：两轮的 `initial_reward` 均为 0.0、`final_reward` 均为 1.0（见 `evals/skillopt/results/*/training_summary.json`）。
  该数值是「关键词覆盖率」而非质量分，详见本轮 Fixed 中的修正说明。
- 新增 CI job `agentskills-ci-check`：调用 [agentskills-ci](https://github.com/damanisme/agentskills-ci) 对 `skills/` 做 frontmatter lint + 0–100 质量分 + 危险命令扫描，产出 Markdown 报告作为 Artifact。
- 新增 CI job `skilldiff-regression`：跑 pax-clarify 行为回归；未配置 live harness 时降级为 recorded demo。
- `scripts/backfill_agentskills_sections.py`：一键为所有 pax-* SKILL.md 补齐 agentskills-ci 要求的 4 个推荐段落与 `Use when ...` 触发词。
- `pax-forge agentskills-ci` 子命令：作为外部 agentskills-ci 工具的 wrapper（优先 PATH 上的 `agentskills-ci` 二进制，回退到 `python -m agentskills_ci`）；CI 的 `agentskills-ci-check` job 现在也走同一个入口，本地 / CI 行为一致。
- `tests/test_loader.py::test_load_versions_consistent_with_registry`：新增一项契约，校验 `registry.json` 和 `versions.json` 的每个 skill 的 layer / version 一致，防止版本漂移。

### Changed
- **pax-clarify / pax-diagnose** 已把 SkillOpt 训练产出的 SkillOpt Cue Map 落回 live SKILL.md（之前仅存在 `--dry-run` 产物中）。
- 所有 18 个 Skill 已补齐 `## Overview` / `## When to Use` / `## Common Pitfalls` / `## Verification Checklist` 四个推荐段落，`description` 均加上 `Use when: ...` 触发词前缀。
- `agentskills-ci-check` CI 从建议性门禁提升为硬门禁：`--min-score 80`，失败直接阻断合并；本地实测平均分 100/100。
- `skilldiff-regression` 在未配置 live harness 时改为始终输出 recorded demo 产物（`evals/skilldiff/latest-recorded-report.md` 文本报告 + 退出码），不再静默 skip；旧的 `latest-orbit.html` 依赖 `skilldiff orbit` 命令，当前 npm 发布版尚不包含，改为文本报告保证 CI 产物可用。
- CONTRIBUTING.md 新增「CI 门禁与外部工具」章节，列出 7 个 job 的类型/门槛、agentskills-ci 评分要求、以及开启 live skilldiff run 的具体 Secret/Variable 名称。
- 修正 v0.2.0 条目中的口径：CI job 数量由 "4 个" 修正为当前实际 7 个。
- 将外部工具口径由 7 个修正为 8 个：新添 agentskills-ci（已 clone 到 `tools/agentskills-ci/`）。

### Fixed
- **`pax-ci` 工作流此前整体非法，所有 job 从未执行**：`Run routing evaluation (real mode)` 步骤的 `if: secrets.DASHSCOPE_API_KEY != ''` 在 step 级 `if` 使用了 `secrets` 上下文，GitHub 在解析阶段直接拒绝整个 workflow 文件（`Invalid workflow file: .github/workflows/pax-ci.yml#L1` / `Unrecognized named-value: 'secrets'`）。证据：2026-10-05 推送 `feat/add-pax-init` 触发的 run `#37257726172` 中 `All jobs` 为空、无 artifact，即 0 个 job 被创建；该行自 workflow 引入提交 `3fc1fb7`（2026-09-29）起就存在，因此 `main` 徽章长期为红与此无关代码问题无关。现改为经 job 级 `env` 中转后再判断（`if: env.DASHSCOPE_API_KEY != ''`）。
- `routing-eval` / `quality-gate` 依赖 `tools/skillEval`、`tools/quality_gate.py`，而 `tools/` 被 `.gitignore` 忽略、CI 检出中不存在，workflow 一旦恢复可执行就会必然失败。两者改为在仓库变量 `PAX_TOOLS_AVAILABLE` 未置 `true` 时显式跳过，并在 job 内断言对应路径存在（缺失即 `::error` 失败，不静默放过）；`skilldiff-regression` 的 recorded demo 步骤同样按 `tools/` 存在性跳过并在 Step Summary 中记录。
- `quality-summary` 原先只在 `contracts-and-tests` / `internal-routing-check` / `quality-gate` 三者皆 `success` 时打印「All quality gates passed」，因此**被跳过的 job 会被误报为「质量门禁失败」**；改为区分 `success` / `skipped` / 失败三类，跳过项显式列为「本次未执行」并说明原因。
- `pull_request.paths` 缺少 `.github/workflows/pax-ci.yml`（`push.paths` 侧已包含），导致仅修改 workflow 的 PR 不触发 CI；已补齐。
- `tests/test_loader.py::test_load_versions_shape`：去掉写死的 `version == "0.1.0"` 断言，改为校验语义版本号形式（`\d+\.\d+\.\d+`），避免下次发版后再次变旧。
- SkillOpt 训练不再因为奖励函数与 `expected_action` 无关而输出恒为 0.888 的空结果。
- SkillOpt patch 步骤不再重复写入 "## SkillOpt Cue Map" 标题：后续 epoch 会把新增条目 merge 到已有块内。
- pax-clarify / pax-orchestrate 不再引用不存在的 `references/domain-dependencies.md`（已在两个 Skill 目录下各存一份），消除 agentskills-ci 的 Referenced path does not exist 错误。
- `skilldiff orbit` 命令在 npm 0.1.0 中尚不存在，但 CI 里之前写了；已改为 `skilldiff run --old --new` recorded 模式并保存文本报告。

## [0.2.0] - 2026-09-30

### Added
- 13 个 Skill 完整填充（从骨架到完整工作流）
- pax-orchestrate MECE 意图分类（6 类意图 + 二级意图）
- pax-orchestrate 四维风险评分（不可逆性/影响范围/不确定性/协调成本）
- pax-orchestrate 路由构建（12 种路由组合表）
- pax-clarify 共识状态机（6 维度 × 5 状态）
- pax-diagnose 存储后端确认（D2 阶段强制检查）
- pax-plan 数据订正守卫（prerequisite + script_language）
- pax-execute 跨仓库守卫（repo + execution_strategy）
- 内部路由评估框架（14 案例，4 维度）
- 真实场景试跑记录（3 个场景）
- skillEval 路由评估数据集（30 案例）
- CI 流水线（4 个 job：contracts-and-tests / routing-eval / internal-routing-check / quality-summary）
- 7 个外部工具安装（SkillOpt / SkillGym / agent-skill-framework / skillEval / Coder Eval / skill-up / skilldiff）

### Changed
- 所有 13 个 Skill 版本升至 0.2.0
- pax-orchestrate description 优化（明确为 pax-family 统一入口）
- L1-L4 skills description 优化（明确通过 pax-orchestrate 调用）
- pax-clarify description 优化（明确何时需要澄清需求）
- 评估目标调整（exact_set_match 从 80% 降至 70%，后提升至 80%）

### Fixed
- 修复测试隔离问题（test_cli_new_creates_skill 改用 cwd）
- 修复 layer-call-legality 契约违规（移除 L0 对 L2 的直接引用）
- 修复 L4 不引用 L1/L0 契约违规

## [0.1.0] - 2026-09-29

### Added
- 家族宪法 `schemas/pax-family.schema.yaml`
- 快照 JSON Schema `schemas/snapshot.schema.json`
- 版本基线 `pax-ops/versions.json`
- 注册表 `pax-ops/registry.json`
- 补丁清单 `pax-ops/patches/manifest.json`
- CLI `pax-forge`：`init / new / validate / register / list / test / version / deprecate / patch apply` 九个子命令
- 7 项契约测试：frontmatter 完整性 / snapshot schema 合法性 / 层间调用合法性 / 版本一致性 / 无环 / 跳过审计 / 门禁行为
- 13 个 Skill 骨架：L0/L1/L2/L3/L4/meta 全覆盖
- 参考文档：severity-criteria / domain-dependencies / compatibility-matrix
