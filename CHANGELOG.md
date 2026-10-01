# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- `pax-monitor` / `pax-rollback` / `pax-test` / `pax-deploy` / `pax-learn`：将家族从 13 个扩展到 18 个（`pax-ops/versions.json` 已同步）。
- `evals/skillopt/train_pax_offline.py`：SkillOpt 闭环训练脚本，修复了之前三个致命 bug（奖励不依赖 `expected_action`、永不更新 skill、奖励已接近天花板），引入 `Action Cue Registry`，实现 rollout → reflect → aggregate → select → update → evaluate 完整循环。
- SkillOpt 训练集 v2：`pax_clarify_train_v2.jsonl` / `pax_clarify_eval_v2.jsonl`（14 + 7 例）+ `pax_diagnose_train_v2.jsonl` / `pax_diagnose_eval_v2.jsonl`（10 + 5 例）。
- 首次跑通 pax-clarify 和 pax-diagnose 训练：两个 Skill 的 `final_reward` 都达到 1.0，improvement = +1.0（见 `evals/skillopt/results/clarify_v2/training_summary.json` 和 `diagnose_v2/training_summary.json`）。
- 新增 CI job `agentskills-ci-check`：调用 [agentskills-ci](https://github.com/damanisme/agentskills-ci) 对 `skills/` 做 frontmatter lint + 0–100 质量分 + 危险命令扫描，产出 Markdown 报告作为 Artifact。
- 新增 CI job `skilldiff-regression`：跑 pax-clarify 行为回归；未配置 live harness 时降级为 recorded demo。
- `scripts/backfill_agentskills_sections.py`：一键为所有 pax-* SKILL.md 补齐 agentskills-ci 要求的 4 个推荐段落与 `Use when ...` 触发词。

### Changed
- **pax-clarify / pax-diagnose** 已把 SkillOpt 训练产出的 SkillOpt Cue Map 落回 live SKILL.md（之前仅存在 `--dry-run` 产物中）。
- 所有 18 个 Skill 已补齐 `## Overview` / `## When to Use` / `## Common Pitfalls` / `## Verification Checklist` 四个推荐段落，`description` 均加上 `Use when: ...` 触发词前缀。
- `agentskills-ci-check` CI 从建议性门禁提升为硬门禁：`--min-score 80`，失败直接阻断合并；本地实测平均分 100/100。
- `skilldiff-regression` 在未配置 live harness 时改为始终输出 recorded demo 产物（`evals/skilldiff/latest-orbit.html`），不再静默 skip。
- CONTRIBUTING.md 新增「CI 门禁与外部工具」章节，列出 7 个 job 的类型/门槛、agentskills-ci 评分要求、以及开启 live skilldiff run 的具体 Secret/Variable 名称。
- 修正 v0.2.0 条目中的口径：CI job 数量由 "4 个" 修正为当前实际 7 个。
- 将外部工具口径由 7 个修正为 8 个：新添 agentskills-ci（已 clone 到 `tools/agentskills-ci/`）。

### Fixed
- SkillOpt 训练不再因为奖励函数与 `expected_action` 无关而输出恒为 0.888 的空结果。
- SkillOpt patch 步骤不再重复写入 "## SkillOpt Cue Map" 标题：后续 epoch 会把新增条目 merge 到已有块内。
- pax-clarify / pax-orchestrate 不再引用不存在的 `references/domain-dependencies.md`（已在两个 Skill 目录下各存一份），消除 agentskills-ci 的 Referenced path does not exist 错误。

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
