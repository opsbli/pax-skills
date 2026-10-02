# pax-* 家族路由评估

本目录包含 pax-* 家族的两套评估工具：

## 评估结果（外部路由基线）

**首次真实模型运行：2026-10-02 18:12 GMT+8**

| 项 | 值 |
|------|------|
| 模型 | `openai/deepseek-flash` @ `api.deepseek.com`，temperature=0 |
| 套件 | pax_routing v2.0 |
| config_hash | `sha256:1112b42b0667f8a0` |
| 数据集 hash | `sha256:5ac842318c8b8fe8`（19 cases） |
| catalog | 18 个 pax skill，内容 hash 固化在 `config.snapshot.yaml` |
| 归档 | skillEval `outputs/pax_routing_v1.0__deepseek-flash__v1/20261002T181204085605+0800` |
| 工作量 | 57/57 turns 成功，0 错误 |

| 指标 | 目标门槛 | 实测 | 判定 |
|------|----------|------|------|
| exact_set_match | ≥0.80 | **100.0%** | PASS |
| top1 | ≥0.85 | **100.0%** | PASS |
| no_skill_rejection | ≥0.90 | **100.0%**（9/9） | PASS |
| false_activation | ≤0.10 | **0.0%** | PASS |
| type_amb | ≥0.70 | **100.0%** | PASS |
| multi_exact | — | n/a（无多 skill gold 题） | — |
| → **GATE** | | | **PASS** |

稳定性：跨 3 次 repeat **100.0% ± 0.0%**，flaky_rate **0.0**，pass@3 = pass^3 = 100%。
效率：1.3s ± 0.5s / turn，1190 ± 63 tokens，0 tool calls（routing_only 预期）。

### 这个数字意味着什么（重要）

100% 真实且可复现，但**它测的不是 skill 区分能力**。重建实际发出去的 prompt 后发现：

> 18 个 skill 里有 **17 个**的 description 自己写着「此 skill 由 pax-orchestrate
> 在编排路由中调用，不要直接选择」；pax-orchestrate 自己写着「所有 pax-family 任务的
> 统一入口……不要直接选择 pax-diagnose、pax-plan、pax-execute 等具体 skill」。

所以 catalog 虽然 18 个条目，但按描述自身的规则只有 1 个是候选的。模型实际在做的是
「遵守 17 条显式禁令」，而不是在 18 个语义上竞争的 skill 之间做判断。

- **正面/歧义/多目标题的 100% 不含信息量**，难度接近 0。
- **真正有信号的是 3 条 reject 题（9/9）**：模型在 18 个看起来都相关的 skill 面前，
  正确地对翻译/天气/概念解释返回了空列表。这是本次基线唯一非平凡的结论。
- **门槛值（0.80/0.85/0.90/0.10/0.70）是从未校准的声明值**，100% 的差距大到看不出
  校准是否合理。要拿这些门槛做真正的发布判断，需要更难的题集。

### 对照组实验：禁令到底贡献了多少（2026-10-02）

上面的疑问已经实验回答了。做法：写 `evals/build_control_subjects.py` 生成一个对照组 skill 集，
剥离 description 里的禁令文本，**保留能力描述**（「此 skill 由 pax-orchestrate 在编排路由中调用，
不要直接选择。」整句删除；「…调用，用于<能力说明>」保留后半句）。同模型、同数据集、同 repeats，
唯一变量是 description 文本。生成脚本带 `--check` 校验漂移。

校验过模型实际看到的 prompt：v2.0 的 user 消息 **1904 字**，对照组 **1107 字**——
**禁令类指令占整个 catalog 的 42%**（13 次「不要直接选择」+ 1 次「应选择 pax-orchestrate」
+ 17 次「在编排路由中调用」，对照组全为 0）。skill_id 集合与正文一字未动。

#### 结果

| 指标 | v2.0（带禁令） | 对照组（无禁令） | Δ |
|------|------|------|------|
| exact_set_match | **57/57 (100.0%)** | **38/57 (66.7%)** | **-33.3pp** |
| top1 | 100.0% | 93.8% | -6.3pp |
| no_skill_rejection | 100.0% (9/9) | 100.0% (9/9) | **0.0** |
| false_activation | 0.0% | 0.0% | 0.0 |
| type_amb | 100.0% | 50.0% | -50.0pp |
| pass^3（3 次全对） | 100% | 42.1% | -57.9pp |
| flaky case 数 | 0 | 9 | +9 |

按类型（exact_set_match）：

| 类型 | v2.0 | 对照组 | Δ |
|------|------|------|------|
| pos | 100.0% | 63.3% | -36.7pp |
| amb | 100.0% | 50.0% | **-50.0pp** |
| multi | 100.0% | 66.7% | -33.3pp |
| **rej** | **100.0%** | **100.0%** | **0.0** |

#### 禁令的实际作用

**19 个错误里 16 个（84%）仍然选中了 pax-orchestrate**——它只是在正确答案上多叠了一个子 skill：

```
pax-orchestrate + pax-diagnose   9 次
pax-orchestrate + pax-clarify    5 次
pax-orchestrate + pax-docs       2 次
pax-review（放弃 orchestrator）   3 次
```

即 pax-orchestrate 在 **48/57（84.2%）** 的对照组判定里仍被选中。禁令真正的功能是
**约束「只选一个」**，不是「让模型选对入口」。模型在无指示下也能识别 pax-orchestrate，
但缺乏抑制并选子 skill 的约束。

**两条 reject 题在对照组仍然 9/9**。这条不靠禁令——模型面对 18 个看似相关的 skill，
对翻译/天气/概念解释照样返回空列表。这是两个实验里唯一完全一致、且非平凡的结论。

**`pax-pos-09`（帮我 review 这个 PR，看有没有安全漏洞）在对照组 3/3 选 `pax-review`**，
理由写得很顺理成章。这条 gold 标签本身就有争议：从纯语义看「review PR 找漏洞」确实像
评审任务，「必须先经 pax-orchestrate」是架构约定而非语义必然。v2.0 的 100% 把这个争议盖住了。

#### 结论

- **禁令贡献 33.3 个百分点**，全部集中在「模型会不会多选子 skill」，与入口识别无关。
- pax-orchestrate 的「统一入口」描述本身已经足够有吸引力，不需要禁令来维持。
- 真正需要设计决策的是：pax-review 这类 L1 skill 面对「看起来就是它的任务」时到底该不该被选中，
  以及多目标请求（multi/amb）是否允许一次选多个 skill。这两个口径决定了 gold 该长什么样，
  在定下来之前，66.7% 与 100% 都不能单独作为发布判断。
- 稳定性差异同样显著：无禁令时 9 个 case 在 3 次 repeat 间摆动，amb 题尤为不稳定（pass^3 只有
  42.1%）。禁令同时也起到了「降低方差」的作用。

运行归档：`skillEval/outputs/pax_routing_v1.0__deepseek-flash__v1/`
（v2.0 = `20261002T181204085605+0800`，对照组 = `20261002T191901228346+0800`）。
输出目录名按**数据集名**而非 suite 名，两个 run 在同一父目录下，靠时间戳区分。

### 修正说明（历史）

本文档 2026-09-30 版本记录的 81.1% / 97.2% / 100% / 0% 无法复现，已删除。三个独立原因：

1. 当时 `suite_version 1.0` 的 `include: [pax-orchestrate]` 让 catalog 里只有**一个** skill，
   模型没有其他选项，正面案例命中率按构造必然接近 100%，测不出任何路由能力。
2. 数据集实际 **19** 条用例，不是 30 条。
3. 当时没有任何运行归档，且 skillEval 对 `--mock` 会显式拒绝下质量结论
   （`synthetic mock run — pipeline smoke only, not a skill-quality verdict`），
   所以那组数字也不可能来自 mock 链路验证。

## 1. 外部路由评估（skillEval routing_only）

测试模型能否根据用户请求正确选择 skill。

### 文件结构

```
evals/
├── sync_subjects.py            # skills/ → evals/subjects/ 的唯一生成入口（--check 可校验漂移）
├── build_control_subjects.py   # subjects/ → 对照组（剥离禁令）+ 对照组套件（--check 可校验漂移）
├── compare_runs.py             # 两次 routing 运行的逐 case A/B 对比（只读，不调 API）
├── datasets/
│   └── pax_routing_v1.0.jsonl  # 19 个路由测试用例（含 # 注释头，读取时跳过）
├── suites/
│   ├── pax_routing.yaml           # 基线套件（suite_version 2.0）
│   └── pax_routing_control.yaml   # 对照组套件（2.0-control，与基线唯一差异是 skills.dir）
├── subjects/                   # 派生产物：由 sync_subjects.py 从 skills/ 生成，勿手工编辑
│   ├── pax-orchestrate/v1/SKILL.md
│   └── ... (共 18 个 skill)
├── subjects_control_no_prohibition/  # 派生产物：仅 description 剥离禁令，勿手工编辑
├── records/
│   └── real_scenario_trial.md       # 预期决策记录（人工编写，未调用模型）
└── results/
    └── internal_routing_results.json # 内部路由评估结果（真实模型运行）
```

### 测试用例分布（实测）

| 类型 | 数量 | 说明 |
|------|------|------|
| pos | 10 | 明确可执行请求，期望路由到 pax-orchestrate |
| amb | 4 | 歧义请求（措辞含糊、缺少上下文） |
| rej | 3 | 非 pax 任务（翻译、天气、概念解释），期望空集 |
| multi | 2 | 多目标请求（诊断+复盘、脚本+报告） |
| **合计** | **19** | |

按主题标签交叉分布：diagnose_fix 5 / feature_dev 2 / refactor 2 / data_ops 2 /
doc_consult 2 / tool_build 1 / review 1 / 纯 reject 3。

### 运行方式

skillEval 克隆在 `C:\Users\sinvi\Documents\codes\agent-skills-tooling\skillEval`（本仓库同级）。
套件内的 `dataset` 与 `skills.dir` 是绝对路径，所以从 skillEval 根目录跑即可：

```bash
cd C:/Users/sinvi/Documents/codes/pax-skills && python evals/sync_subjects.py   # skills/ 变了才需要
cd C:/Users/sinvi/Documents/codes/agent-skills-tooling/skillEval

# 1. 只校验：不调 API、不写盘、不花钱
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline plan --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing.yaml" --healthcheck

# 2. mock 冒烟：验证链路，结果不可用于质量判断
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline run --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing.yaml" --mock --confirm

# 3. 真实运行：57 次请求（19 用例 × 3 repeats）
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline run --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing.yaml" --confirm --confirm-egress

# 3b. 对照组（先重建对照组 skill 集，再跑同一命令换套件）
cd C:/Users/sinvi/Documents/codes/pax-skills && python evals/build_control_subjects.py
cd C:/Users/sinvi/Documents/codes/agent-skills-tooling/skillEval
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline run --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing_control.yaml" --confirm --confirm-egress

# 3c. 自检对照组有没有漂移（不调 API）
cd C:/Users/sinvi/Documents/codes/pax-skills && python evals/build_control_subjects.py --check

# 3d. 两次运行逐 case 对比（不调 API）
cd C:/Users/sinvi/Documents/codes/pax-skills
python evals/compare_runs.py \
  ../agent-skills-tooling/skillEval/outputs/pax_routing_v1.0__deepseek-flash__v1/<run_a> \
  ../agent-skills-tooling/skillEval/outputs/pax_routing_v1.0__deepseek-flash__v1/<run_b> \
  --dataset evals/datasets/pax_routing_v1.0.jsonl --label-a v2.0 --label-b 对照组

# 4. 只重跑评分（不动模型，已归档结果改 scoring 后用）
PYTHONUTF8=1 .venv/Scripts/python.exe -m workflows.score_routing \
  --dir outputs/pax_routing_v1.0__deepseek-flash__v1/<execution-id>
```

密钥与端点写在 skillEval 的 `.env`（已 gitignore），**绝不**写进套件：

```bash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=sk-...
```

DeepSeek 官方 OpenAI 兼容端点，2026-10-02 实测；该账号可用模型为 `deepseek-flash`
与 `deepseek-v4-pro`（用 `GET /models` 确认，不要凭记忆写 model 串）。

`--confirm-egress` 是 skillEval 强制的外部数据确认：plan 会先打印外发清单（prompt +
skill 元数据），确认它符合预期再放行。

### 评分门槛

| 指标 | 门槛 |
|------|------|
| exact_set_match | >= 0.80 |
| top1 | >= 0.85 |
| no_skill_rejection | >= 0.90 |
| false_activation | <= 0.10 |
| type_amb | >= 0.70 |

当前门槛全 PASS 且实测 100%（见上方「这个数字意味着什么」），说明题集太简单，
门槛还没有起到区分作用。

## 2. 内部路由评估（真实模型调用）

测 pax-orchestrate 的**内部**决策：意图分类（W1）、风险评分（W2）、诊断必要性（W3）、路由构建（W4）。
与第 1 节是两层：第 1 节测「模型要不要选 pax-orchestrate」，本节测「pax-orchestrate 内部判得对不对」。

### 文件

```
evals/datasets/pax_internal_routing_v1.0.json   # 数据集（14 案例）
evals/run_internal_routing_eval.py               # 评估脚本（v2.0，真实调用模型）
evals/results/internal_routing_results.json      # 最近一次真实运行结果
tests/test_orchestrate_routing.py                # pytest（5 个，自洽性测试，不测真实 skill）
```

### 基线结果（2026-10-02，deepseek-flash，temperature=0，repeats=3）

14 案例 × 3 次 = 42 次判定：

| 口径 | 通过 | 说明 |
|------|------|------|
| 原始 | 14/42 (33.3%) | 含 gold 要求但契约未定义的字段，**不可单独引用** |
| 剔除 `confidence` | **33/42 (78.6%)** | 模型真实表现 |

| 类别 | 剔除后 | 原始 |
|------|--------|------|
| intent_classification | 19/21 (90.5%) | 0/21 (0.0%) |
| risk_scoring | 6/9 (66.7%) | 6/9 (66.7%) |
| route_building | 5/9 (55.6%) | 5/9 (55.6%) |
| cross_repo_detection | 3/3 (100.0%) | 3/3 (100.0%) |

稳定性：1/14 案例跨 3 次不一致（`pax-route-fd-01`，2/3）。tokens：input 139,461 / output 42,830。

### 逐检查项（42 次判定）

| 检查项 | 通过 |
|--------|------|
| primary_intent | 21/21 |
| diagnose_required | 9/9 |
| uncertainty | 9/9 |
| coordination_cost | 9/9 |
| secondary_intent | 19/21 |
| cross_repo / execution_strategy_required | 3/3 |
| route | 8/9 |
| irreversibility / impact_scope / risk_score / risk_level | 6/9 |
| storage_backend_required | 6/9 |
| confidence | 0/21 ← gold 要求但 SKILL.md 未定义 |

### 结论

**契约明确且自洽的地方，模型基本全对**：`primary_intent` 21/21、`diagnose_required` 9/9、
`uncertainty` / `coordination_cost` 各 9/9。

**失败集中在契约本身不够具体、或 gold 与契约逻辑冲突的地方**——4 项，已写入结果的
`gold_contract_issues` 字段，不计入模型能力：

1. **`confidence` 字段不存在**：7 条 intent 案例的 gold 都要求 confidence（high/medium/low），
   但 W1–W4 从未定义该字段，模型只能返回 `None`，21 次判定全灭。
2. **`pax-risk-high-01` 的四维取值无法从 prompt 推导**：gold 3/3/2/2=10 (high) 内部自洽
   （且命中 W2「不可逆性 3 且影响范围 3 → 强制 high」），但契约对 `impact_scope=3` 的标准是
   「系统级、跨团队、跨系统、全用户」，prompt 只说「把旧表的数据迁移到新表」，无系统级信号。
   模型三次一致给 2/2/2/2=8 (medium)。
3. **`pax-route-df-01` 的 gold 与契约自身逻辑冲突**：gold 给 `secondary_intent=[]` 却要求
   `storage_backend_required=true`；而 W4 的条件是 `primary == "data_ops" or "data_integrity" in secondary`，
   本案例 primary=diagnose_fix、secondary=[]，两个条件都不满足，契约强制 false。gold 按契约逻辑就是错的。
4. **`pax-intent-df-01` 的 ux_error 无判定样例**：gold `secondary=[]`，但契约对 ux_error 的触发条件
   写的是「前端报错、交互异常、UI 缺陷」，表单字段校验报错算不算没给样例，模型 3 次里 1 次标为 ux_error。

### 使用方式

```bash
PY=../agent-skills-tooling/skillEval/.venv/Scripts/python.exe   # 任一装好 openai 的解释器

# 真实运行（repeats=3 → 42 次请求）
$PY evals/run_internal_routing_eval.py --repeats 3

# 不调 API，看将发送的系统提示（自检提示词有没有越界）
$PY evals/run_internal_routing_eval.py --dry-run

# 不重新调用，用已有结果重算汇总
$PY evals/run_internal_routing_eval.py --rescore

# 自洽性测试（stub 对金标，不测真实 skill）
$PY -m pytest tests/test_orchestrate_routing.py -v
```

系统提示 = SKILL.md 的 W1–W4 原文，**未注入契约外的任何澄清**——否则衡量的是补丁而不是 skill 本身。
密钥从 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` 环境变量取。pax-skills 无自带 venv。

### 关于 `tests/test_orchestrate_routing.py`

这 5 个 pytest **不是**对 pax-orchestrate 的能力评估：文件里手写的 `_classify_intent()` /
`_build_route()` 是关键词匹配桩，从未读过 SKILL.md，因此只证明「桩的输出」与「数据集 gold」一致。
它们保留为「意图 → 路由映射」的回归基线：改 SKILL.md 的路由表时应会失败并提醒。

## 3. 真实场景试跑（预期决策记录，未实际调用模型）

`evals/records/real_scenario_trial.md` 里的「预期路由决策」是人工编写的参考基准，
后面的「测试结果」JSON 数值与之完全相同——**没有调用过模型**，不是实测结果。
该文件只应作为「这些场景应该输出什么」的人工基准参考，不可引用为验证结论。
真正跑过模型的是第 1 节（外部路由）和第 2 节（内部路由）。

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
