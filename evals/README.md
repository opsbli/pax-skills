# pax-* 家族路由评估

本目录包含 pax-* 家族的两套评估工具：

## 评估结果（2026-09-30）

| 指标 | 结果 | 目标 | 状态 |
|------|------|------|------|
| Exact match | 81.1% | ≥80% | PASS |
| Top-1 accuracy | 97.2% | ≥85% | PASS |
| No-Skill rejection | 100% | ≥90% | PASS |
| False activation | 0% | ≤10% | PASS |

模型：sensenova-6.8-flash-lite
数据集：30 案例，3 repeats

## 1. 外部路由评估（skillEval routing_only）

测试模型能否根据用户请求正确选择 skill。

### 文件结构

```
evals/
├── datasets/
│   └── pax_routing_v1.0.jsonl      # 30 个路由测试用例
├── suites/                           # 评估套件配置（在 tools/skillEval/evals/suites/）
├── subjects/                        # 被测 skills（symlink 到 skills/）
│   ├── pax-orchestrate/v1/SKILL.md
│   ├── pax-clarify/v1/SKILL.md
│   └── ...
├── records/
│   └── real_scenario_trial.md       # 真实场景试跑记录
└── results/
    └── internal_routing_results.json # 内部路由评估结果
```

### 测试用例分布

| 类型 | 数量 | 说明 |
|------|------|------|
| diagnose_fix | 5 | 诊断修复（报错、性能退化） |
| feature_dev | 4 | 功能开发（导出、审批） |
| refactor | 3 | 重构优化（拆分、依赖） |
| data_ops | 3 | 数据操作（订正、迁移） |
| doc_consult | 3 | 文档咨询（解释、方案） |
| tool_build | 2 | 工具构建（脚本、自动化） |
| ambiguous | 5 | 歧义案例 |
| reject | 5 | 非 pax 任务 |

### 运行方式

```bash
cd tools/skillEval
python -m pipeline run --suite evals/suites/pax_routing.yaml --confirm --confirm-egress
```

### 评分门槛

| 指标 | 门槛 |
|------|------|
| exact_set_match | >= 0.80 |
| top1 | >= 0.85 |
| no_skill_rejection | >= 0.90 |
| false_activation | <= 0.10 |

## 2. 内部路由评估（单元测试）

测试 pax-orchestrate 的内部路由逻辑：意图分类、风险评分、路由构建。

### 文件

```
evals/datasets/pax_internal_routing_v1.0.json   # 数据集（14 案例）
evals/run_internal_routing_eval.py               # 评估脚本（框架）
tests/test_orchestrate_routing.py                # pytest 测试（5 个测试）
```

### 测试覆盖

| 类别 | 用例数 | 说明 |
|------|--------|------|
| intent_classification | 7 | MECE 意图分类 |
| risk_scoring | 3 | 四维风险评分 |
| route_building | 3 | 路由构建 |
| cross_repo_detection | 1 | 跨仓库检测 |
| **合计** | **14** | |

### 测试覆盖

| 测试 | 说明 |
|------|------|
| test_intent_classification | 验证意图分类逻辑（7 案例） |
| test_route_building | 验证路由构建逻辑（3 案例） |
| test_skill_description_mentions_entry_point | 验证 pax-orchestrate 描述 |
| test_l1_skills_mention_orchestrate | 验证 L1 skills 描述 |
| test_clarify_description_mentions_clarification_needed | 验证 pax-clarify 描述 |

### 使用方式

```bash
# 运行 pytest 测试
.venv/Scripts/python.exe -m pytest tests/test_orchestrate_routing.py -v

# 运行评估脚本（框架模式）
.venv/Scripts/python.exe evals/run_internal_routing_eval.py
```

## 3. 真实场景试跑

验证 pax-orchestrate 路由逻辑在真实场景中的表现。

### 场景

| 场景 | 意图 | 风险 | 路由 | 跨仓库 |
|------|------|------|------|--------|
| CMDB 数据订正 | data_ops | high (9) | clarify→diagnose→plan→execute→review | ✓ |
| 新功能开发 | feature_dev | medium (6) | clarify→plan→execute→review | ✗ |
| 文档咨询 | doc_consult | low (4) | clarify | ✗ |

### 文件

```
evals/records/real_scenario_trial.md
```

## 4. 文件变更

评估文件不受 `.gitignore` 限制，应纳入版本控制。
