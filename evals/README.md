# pax-* 家族路由评估

本目录包含 pax-* 家族的两套评估工具：

## 1. 外部路由评估（skillEval routing_only）

测试模型能否根据用户请求正确激活 pax-orchestrate。

### 文件结构

```
evals/
├── datasets/
│   └── pax_routing_v1.0.jsonl      # 19 个路由测试用例
├── suites/
│   └── pax_routing.yaml            # 评估套件配置
└── subjects/                        # 被测 skills（symlink 到 skills/）
    ├── pax-orchestrate/v1/SKILL.md
    ├── pax-clarify/v1/SKILL.md
    └── ...
```

### 测试用例分布

| 类型 | 数量 | 说明 |
|------|------|------|
| pos  | 10   | 明确意图，应激活 pax-orchestrate |
| amb  | 4    | 模糊意图，可能映射到多个 skill |
| rej  | 3    | 非技术请求，不应激活任何 skill |
| multi| 2    | 需要多 skill 协作 |

### 运行方式

```bash
cd tools/skillEval
python -m pipeline plan --suite ../../evals/suites/pax_routing.yaml
python -m pipeline run --suite ../../evals/suites/pax_routing.yaml
python -m pipeline score --suite ../../evals/suites/pax_routing.yaml
```

### 评分门槛

| 指标 | 门槛 |
|------|------|
| exact_set_match | >= 0.80 |
| top1 | >= 0.85 |
| no_skill_rejection | >= 0.90 |
| false_activation | <= 0.10 |
| type_amb | >= 0.70 |

## 2. 内部路由评估（单元测试）

测试 pax-orchestrate 的内部路由逻辑：意图分类、风险评分、诊断必要性决策、路由构建。

### 文件

```
evals/datasets/pax_internal_routing_v1.0.json
```

### 测试覆盖

| 类别 | 用例数 | 说明 |
|------|--------|------|
| intent_classification | 10 | MECE 意图分类 |
| risk_scoring | 5 | 四维风险评分 |
| diagnose_required | 7 | 诊断必要性决策 |
| route_building | 7 | 路由构建 + 标注 |
| skip_conditions | 5 | 跳过诊断条件 |
| cross_repo_detection | 4 | 跨仓库检测 |
| **合计** | **38** | |

### 用例示例

```json
{
  "id": "IC-001",
  "name": "明确缺陷信号 → diagnose_fix",
  "input": "生产环境 CMDB 字段校验报错...",
  "expected_primary": "diagnose_fix",
  "expected_secondary": ["data_integrity"],
  "rationale": "有明确错误信息 + 既有行为异常"
}
```

### 使用方式

内部路由评估用例可用于：
1. 手动验证：人工运行 pax-orchestrate 并对比预期结果
2. 自动化测试：集成到 pytest 测试套件
3. 回归测试：Skill 更新后重新运行用例

## 3. 文件变更

评估文件不受 `.gitignore` 限制，应纳入版本控制。
