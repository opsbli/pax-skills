# pax-*

**Pact-based Agreement eXecution** —— 一个以软件工程方法构建的 AI Skill 家族。

## 特性

- **可组合**：跨 Skill 状态通过结构化快照通信
- **可审计**：每个阶段的状态、决策、跳过、失败全部留痕
- **可验证**：契约测试强制家族规则
- **可版本化**：家族统一版本线，兼容矩阵显式管理
- **可演化**：`pax-forge` 生成 + `pax-evolve` 自进化

## 家族构成

| 层 | Skill | 可选 | 职责 |
|---|---|---|---|
| meta | `pax-forge` | 否 | 生成、校验、注册（**是 CLI，不是可注册 skill**，不参与编排） |
| L0 | `pax-orchestrate` | 否 | 路由、风险分级 |
| L1 | `pax-clarify` | 否 | 共识状态机 |
| L1 | `pax-diagnose` | 是 | 根因诊断 |
| L1 | `pax-plan` | 否 | 结构化规划 |
| L1 | `pax-execute` | 否 | 契约约束下执行 |
| L1 | `pax-review` | 否 | 独立评审门禁 |
| L1 | `pax-monitor` | 是 | 运行中监控与告警 |
| L1 | `pax-rollback` | 是 | 自动化回滚 |
| L1 | `pax-test` | 是 | 自动化测试生成 |
| L1 | `pax-deploy` | 是 | 部署流程编排 |
| L1 | `pax-learn` | 是 | 经验沉淀与知识图谱 |
| L2 | `pax-advisor` | 是 | 单点咨询 |
| L2 | `pax-council` | 是 | 多专家盲审 |
| L3 | `pax-worker-research` | 是 | 研究型子任务 |
| L3 | `pax-worker-implement` | 是 | 实现型子任务 |
| L4 | `pax-verify` | 是 | 运行中验证 |
| L4 | `pax-evolve` | 是 | 自进化 |
| L4 | `pax-docs` | 是 | 文档沉淀 |
| L4 | `pax-init` | 是 | 项目接入与初始化（扫描技术栈 → 生成 AGENTS.md + `.pax/project-profile.json` → 创建 `.pax/`） |

## 快速开始

```bash
pip install -e ".[dev]"

# 生成一个新 skill
pax-forge new pax-foo --layer L1 --description "..."
pax-forge validate skills/pax-foo
pax-forge register skills/pax-foo

# 跑家族契约测试
pax-forge test

# 列出所有注册 skill
pax-forge list
```

## 项目接入

把一个已有项目接进家族（由用户直接调用，不经编排路由）：

```text
用户：把这个项目接入 pax-family → pax-init 扫描技术栈 →
      生成 AGENTS.md + .pax/project-profile.json → 创建 .pax/
```

## 运行时目录（single-source-of-truth）

家族的身份与纪律由两套**运行时契约**支撑，分散在家族根的两个顶层目录，但同属一份 single-source-of-truth：

- `schemas/pax-family.schema.yaml` —— 家族契约（层级、命名、必填 frontmatter/章节、声明的检查项）
- `schemas/snapshot.schema.json` —— 快照结构的权威定义
- `pax-ops/versions.json` —— 家族版本线（版本唯一来源）
- `pax-ops/registry.json` —— 已注册 skill 登记
- `pax-ops/patches/` —— 版本补丁

设计要点：

- 这些文件属于**家族运行时**，不是单个目标项目的产物。`pax-forge` 用它们判定“家族根”并加载契约；`pax-init` 引导新 family 副本时把整套复制进骨架（仅限空目录）。
- 业务项目接入时**无需、也不应复制**它们（避免家族版本漂移），门禁从运行时时读取（见 `pax-orchestrate`）。
- 它们**刻意独立于 `.pax/`**：`.pax/` 是产物/快照目录（`pax-snapshot.yaml`、`project-profile.json`），承载任务与项目产物。契约与产物分层存放，不要混入 `.pax/`。

## 设计文档

见 `docs/pax-family-design.md`。

## 路由评估

**当前有效结论以 `evals/README.md` 为准**：那里有完整方法、门槛性质说明与可信度边界。
本节只给入口，不复制任何未经归档校对的数字。

| 层 | 测什么 | 基线（含归档日期） |
|---|---|---|
| 外部路由 | 模型面对用户请求时选不选 `pax-orchestrate` | 基线 100%；对照组（剥离 description 禁令）71.1%；28.9pp 差距已归档为「设计代价」（2026-10-03） |
| 内部路由 | `pax-orchestrate` 内部四步决策（意图 / 风险 / 诊断必要性 / 路由） | 最近一次归档：**44 题** × 5 repeats，能力分 90.8%，GATE PASS（2026-10-05，跑的是 dataset **1.7**） |
| pax-diagnose | 严重度分级 / 复现状态 / 存储后端确认 | 25 场景 × 5 repeats，能力分 99.2%，GATE PASS（2026-10-05） |

评估数据集：`evals/datasets/`（外部 30 案例；内部 **54 案例，dataset version 1.8**）
评估套件：`evals/suites/pax_routing.yaml`（依赖的 skillEval 在本地是**同级目录**副本；
CI 里由 `routing-eval` job 以 `sparse-checkout` 从同级仓库 `sinvi/agent-skills-tooling` 拉取，均不经过 `tools/`）
运行方式：见 `evals/README.md` 第 2、3 节

⚠️ **内部路由的数字与数据集版本已不同步**：dataset 已从 1.7（44 题）升到 **1.8（54 题）**——
新增 10 条 `extension_route_triggering`（覆盖 monitor / rollback / test / deploy / learn
5 个 L1 扩展 skill，每 skill 2 题，全部 holdout；变更记录见 `evals/README.md` 的 v1.8 行）。
上表 90.8% 那行**跑的是 1.7，不覆盖这 10 题**。
要给出 1.8 的基线需重跑真实模型评估（`evals/run_internal_routing_eval.py`，会产生费用）；
在那之前，请勿把 90.8% 当作「当前数据集的成绩」。

⚠️ 两处极易误读，务必注意：

- `tests/test_orchestrate_routing.py` 的 5 个 pytest **不是**能力评估：里面是手写关键词桩，
  从未读过 `SKILL.md`，仅作为「意图 → 路由映射」的回归基线。
- `evals/records/real_scenario_trial.md` **没有调用过模型**，其「测试结果」与人工预期完全相同，
  只能当作「这些场景应该输出什么」的人工基准，**不可引用为验证结论**。

> 历史：本文件曾记录 2026-09-30 的 81.1% / 97.2% / 100% / 0% 一组数字。
> `evals/README.md` 已确认其**无法复现**并删除（当时 catalog 只含 1 个 skill、数据集实际 19 条而非 30 条、
> 且无任何运行归档），详细原因见该文件第 1 节「修正说明（历史）」。
> 本节自此不再复制未存档的数字——要引用指标，请引 `evals/README.md` 的对应小节。

## 贡献

见 `CONTRIBUTING.md`。

## 版本

本项目有**两个独立版本维度**，不要互相推导：

| 维度 | 权威源 | 含义 |
|---|---|---|
| 家族版本 | `pax-ops/versions.json` 的 `version`（当前 `1.0.0`） | 19 个 skill 的整体版本，也是各 skill frontmatter `version` 的来源 |
| 工具包版本 | `pyproject.toml` / `src/pax/__init__.py`（`pax-forge --version`） | `pax-forge` CLI 自身的版本，独立发版 |
| 快照格式版本 | `schemas/snapshot.schema.json` 的 `meta.version`（当前 `2.0`） | 快照结构版本；改必填字段即 bump |
