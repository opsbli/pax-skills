# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

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
