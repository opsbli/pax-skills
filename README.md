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
| meta | `pax-forge` | 否 | 生成、校验、注册 |
| L0 | `pax-orchestrate` | 否 | 路由、风险分级 |
| L1 | `pax-clarify` | 否 | 共识状态机 |
| L1 | `pax-diagnose` | 是 | 根因诊断 |
| L1 | `pax-plan` | 否 | 结构化规划 |
| L1 | `pax-execute` | 否 | 契约约束下执行 |
| L1 | `pax-review` | 否 | 独立评审门禁 |
| L2 | `pax-advisor` | 是 | 单点咨询 |
| L2 | `pax-council` | 是 | 多专家盲审 |
| L3 | `pax-worker-*` | 是 | 有界任务执行 |
| L4 | `pax-verify` | 是 | 运行中验证 |
| L4 | `pax-evolve` | 是 | 自进化 |
| L4 | `pax-docs` | 是 | 文档沉淀 |

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

## 设计文档

见 `docs/pax-family-design.md`。

## 路由评估

pax-orchestrate 路由评估结果（2026-09-30）：

| 指标 | 结果 | 目标 |
|------|------|------|
| Exact match | 81.1% | ≥80% |
| Top-1 accuracy | 97.2% | ≥85% |
| No-Skill rejection | 100% | ≥90% |
| False activation | 0% | ≤10% |

评估数据集：`evals/datasets/pax_routing_v1.0.jsonl`（30 案例）
评估套件：`tools/skillEval/evals/suites/pax_routing.yaml`

内部路由测试：`tests/test_orchestrate_routing.py`（5 个测试）
真实场景试跑：`evals/records/real_scenario_trial.md`

## 贡献

见 `CONTRIBUTING.md`。

## 版本

家族版本见 `pax-ops/versions.json`（当前 v0.2.0）。
