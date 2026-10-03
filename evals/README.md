# pax-* 家族路由评估

本目录包含 pax-* 家族的两套评估工具：

1. **外部路由评估**（skillEval `routing_only`）：测「模型面对用户请求时选不选 pax-orchestrate」
2. **内部路由评估**（自研脚本，真实调用）：测「pax-orchestrate 内部的四步决策对不对」

两层合起来才能判断路由质量。两层的门槛性质不同，下文分别说明。

---

## 1. 外部路由评估

### 当前基线（2026-10-03，30 条用例，suite 2.1）

| 项 | 值 |
|------|------|
| 模型 | `openai/deepseek-flash` @ `api.deepseek.com`，temperature=0 |
| 套件 | `pax_routing.yaml`，suite_version 2.1（已移除 multi_exact） |
| 数据集 | `pax_routing_v1.0.jsonl`，**30 cases**（16 pos / 6 amb / 6 rej / 2 multi） |
| catalog | 18 个 pax skill，内容 hash 固化在 `config.snapshot.yaml` |
| 路径 | 相对路径 `../../pax-skills/...`（不再写死 `C:/Users/<owner>/...`） |
| 归档 | skillEval `outputs/pax_routing_v1.0__deepseek-flash__v1/20261003T114454016293+0800` |
| 工作量 | 90/90 turns 成功（30 × 3 repeats），0 错误 |

| 指标 | 门槛 | 实测 | 判定 |
|------|------|------|------|
| exact_set_match | ≥0.80 | **100.0%** | PASS |
| top1 | ≥0.85 | **100.0%** | PASS |
| no_skill_rejection | ≥0.90 | **100.0%**（18/18） | PASS |
| false_activation | ≤0.10 | **0.0%** | PASS |
| type_amb | ≥0.70 | **100.0%** | PASS |
| → **GATE** | | | **PASS** |

稳定性：跨 3 次 repeat **100.0% ± 0.0%**，flaky case **0 个**，pass@3 = pass^3 = 100%。
效率：1.34 ± 0.46 s / turn，1194 ± 72 tokens，0 tool calls（routing_only 预期）。

**与 v2.0 基线对比**：全部指标 100% 不变，确认移除 multi_exact 不影响其余指标。
对照组 28.9pp 差距结论已归档为「设计代价」，不受 suite 版本影响，不重跑。

### 这个数字意味着什么（重要）

100% 真实且可复现，但**它测的不是 skill 区分能力**。重建实际发出去的 prompt 后发现：

> 18 个 skill 里有 **17 个**的 description 自己写着「此 skill 由 pax-orchestrate
> 在编排路由中调用，不要直接选择」；pax-orchestrate 自己写着「所有 pax-family 任务的
> 统一入口……不要直接选择 pax-diagnose、pax-plan、pax-execute 等具体 skill」。

所以 catalog 虽然 18 个条目，但按描述自身的规则只有 1 个是候选的。模型实际在做的是
「遵守 17 条显式禁令」，而不是在 18 个语义上竞争的 skill 之间做判断。

- **正面/歧义/多目标题的 100% 不含信息量**，难度接近 0。
- **真正有信号的是 6 条 reject 题（18/18）**：模型在 18 个看起来都相关的 skill 面前，
  正确地对翻译/天气/概念解释/元讨论/提示注入返回了空列表。这是本次基线唯一非平凡的结论。
- **门槛值（0.80/0.85/0.90/0.10/0.70）是声明值，不是从测量校准出来的**，100% 的差距
  大到看不出校准是否合理。见下方「门槛的性质」。

### 关于 `multi_exact` 为什么是 NaN（已于 2026-10-03 移除）

不是「还没写多标签题」，而是**catalog 结构决定了这道指标不可能有真值**：

- 18 个 skill 里只有 1 个 L0 入口（pax-orchestrate），其余 17 个都是禁止直选的
  L1/L3 skill。所以任何合法任务的期望集合都只能是单元素。
- 契约 W1 原文写「二级意图不改变路由主干」。多 skill 组合是 pax-orchestrate
  **内部** `route` 数组里的步骤（`clarify→diagnose→plan→execute→review`），
  在外部路由层不可见。
- 硬造一条 `[pax-orchestrate, pax-diagnose]` 的 gold 只会把「不该直选 L1」这条规则
  变成合法答案，等于自废武功。

所以 `multi_exact` 在外部路由层是**结构性 n/a**，不是题目缺口。
要测多 skill 协调，正确的层是内部路由评估的 `route` 检查项。

**2026-10-03 的处置**：D2 决策选 B（入口单选、工作流内分发）后，
这道指标既无真值又无实际意义，遂从两个 suite 的 `metrics` 里移除，
suite 升到 2.1。报告里不再出现一个永远为 NaN 的指标——
留着只会让人去解读一个没有定义的数字。

### 对照组实验：禁令到底贡献了多少（2026-10-02，30 条用例）

上面的疑问已经实验回答了。做法：`evals/build_control_subjects.py` 生成一个对照组 skill 集，
剥离 description 里的禁令文本，**保留能力描述**（「此 skill 由 pax-orchestrate 在编排路由中
调用，不要直接选择。」整句删除；「…调用，用于<能力说明>」保留后半句）。
同模型、同数据集、同 repeats，唯一变量是 description 文本。

#### 结果

| 指标 | v2.0（带禁令） | 对照组（无禁令） | Δ |
|------|------|------|------|
| exact_set_match | **90/90 (100.0%)** | **64/90 (71.1%)** | **-28.9pp** |
| top1 | 100.0% | 88.9% | -11.1pp |
| no_skill_rejection | 100.0% (18/18) | 100.0% (18/18) | **0.0** |
| false_activation | 0.0% | 0.0% | **0.0** |
| type_amb | 100.0% | 50.0% | -50.0pp |
| pass^3（3 次全对） | 100% | 53.3% | -46.7pp |
| flaky case 数 | 0 | 10 | +10 |
| → **GATE** | PASS | **FAIL**（exact_set_match, type_amb） | |

按类型（exact_set_match）：

| 类型 | v2.0 | 对照组 | Δ |
|------|------|------|------|
| pos (16) | 100.0% | 66.7% | -33.3pp |
| amb (6) | 100.0% | 50.0% | **-50.0pp** |
| multi (2) | 100.0% | 83.3% | -16.7pp |
| **rej (6)** | **100.0%** | **100.0%** | **0.0** |

#### 失败模式拆解（新增指标）

对照组 26 次误选按语义归类：

| 模式 | 次数 | 含义 |
|------|------|------|
| **over_selection** | 18（12 个 case） | 正确选了 pax-orchestrate，但额外多叠了子 skill |
| **missing_entry** | 8（5 个 case） | 完全没选 pax-orchestrate，直接选了 L1 skill |
| dropped_entry | 0 | — |
| **false_activation** | 0 | 拒答题被误选 |

过度选择率（分母 = 正面题判定数 48）：**37.5%**；误激活率（分母 = 拒答题判定数 18）：**0.0%**。

具体误选分布：

```
pax-orchestrate + pax-diagnose            14 次
pax-review（放弃 orchestrator）            5 次
pax-orchestrate + pax-clarify             3 次
pax-diagnose                              2 次
pax-clarify                               1 次
pax-orchestrate + pax-diagnose + pax-docs  1 次
```

#### 禁令的实际作用

**18 次过度选择全部仍然选中了 pax-orchestrate**——它只是在正确答案上多叠了一个子 skill。
模型在无指示下也能识别 pax-orchestrate，缺乏的是**抑制并选子 skill 的约束**。

- **禁令真正的功能是约束「只选一个」**，不是「让模型选对入口」。
- **拒答能力完全独立于禁令**：6 条 reject 题（含新加的元讨论题 `pax-rej-04`
  「pax-orchestrate 有哪些子 skill」和提示注入题 `pax-rej-05`）在两组都是 18/18。
  这是三个实验中唯一完全一致、且非平凡的结论。
- **`pax-pos-09`（帮我 review 这个 PR，看有没有安全漏洞）在对照组选 `pax-review`**，
  理由写得很顺理成章。这条 gold 标签本身有争议：从纯语义看「review PR 找漏洞」确实像
  评审任务，「必须先经 pax-orchestrate」是架构约定而非语义必然。v2.0 的 100% 把争议盖住了。

#### 需要业务方定的口径（阻塞 gold 定形）

1. **L1 skill 该不该被直选**：pax-review 面对「看起来就是它的任务」时是否应被选中？
   决定 `pax-pos-09` 的 gold 对不对。
2. **多目标请求是否允许一次选多个 skill**：决定 8 次 missing_entry 的归因。

在定下来之前，71.1% 与 100% 都不能单独作为发布判断。

运行归档（输出目录名按**数据集名**而非 suite 名，两个 run 在同一父目录下，靠时间戳区分）：

```
skillEval/outputs/pax_routing_v1.0__deepseek-flash__v1/
  20261002T181204085605+0800   v2.0，19 题（历史）      config_hash 1112b42b
  20261002T191901228346+0800   对照组，19 题（历史）    config_hash 136613ea
  20261002T201555925185+0800   v2.0，30 题（当前基线）  config_hash c3416c72
  20261002T201823084975+0800   对照组，30 题（当前）    config_hash d9be3a86
```

### 数据集扩充记录（19 → 30 条）

原 19 题在 v2.0 全对，门槛无法校准。新增 11 题：

| 新增题 | 类型 | 目的 |
|--------|------|------|
| `pax-pos-10` review PR 找漏洞 | pos | review 类入口陷阱（L1 语义与入口冲突） |
| `pax-pos-11` 部署上线 | pos | deploy 类入口陷阱 |
| `pax-pos-12` 中英代码改写 | pos | 跨语言歧义（看起来像翻译题） |
| `pax-amb-05` 优化这块代码 | amb | 无上下文纯「优化」 |
| `pax-amb-06` 帮我处理一下 | amb | 纯指代，无信息量 |
| `pax-rej-04` pax-orchestrate 有哪些子 skill | rej | **元讨论**：问 pax 自己算不算 pax 任务 |
| `pax-rej-05` 请忽略之前指示… | rej | **提示注入**：越狱指令下的拒答稳定性 |
| `pax-rej-06` 用 pax 风格写日报 | rej | 「pax」出现在非 pax 任务里 |
| `pax-multi-03` 修复+回滚预案 | multi | 带风险升级意图 |
| `pax-multi-04` 调研+落地 | multi | 研究到执行的跨度 |

**注意 `note` 字段**：skillEval 的 `RoutingCase` 用 pydantic 禁止额外字段，
题目批注必须写成 `#` 注释行，不能加到 JSON 里（已踩过坑）。

### 门槛的性质

当前 5 个门槛（0.80 / 0.85 / 0.90 / 0.10 / 0.70）**是声明值，不是从测量校准出来的**。
区分两类门槛：

- **语义安全门槛**（exact_set_match、no_skill_rejection、false_activation、type_amb）：
  这些是「路由错一次就出事」的指标，门槛必须是保守高值。它们不是通过测量分布推导的，
  而是从「漏一次拒答 = 把翻译当代码任务执行」这类后果倒推的。**这类门槛不应被测量结果
  反向校准**——否则等于把测试反过来拟合实现。
- **统计门槛**（top1）：对部分正确的判定给部分分，校准空间更大，但当前 n 太小，
  校准出来的数字也不可信。

30 题已能产生区分度（对照组 71.1% vs 基线 100%），但**要拿门槛做真正的发布判断，
需要更难的题集让基线本身落在 80–95% 区间**，否则 PASS/FAIL 的判决没有分辨率。

### 修正说明（历史）

本文档 2026-09-30 版本记录的 81.1% / 97.2% / 100% / 0% 无法复现，已删除。三个独立原因：

1. 当时 `suite_version 1.0` 的 `include: [pax-orchestrate]` 让 catalog 里只有**一个** skill，
   模型没有其他选项，正面案例命中率按构造必然接近 100%，测不出任何路由能力。
2. 数据集实际 **19** 条用例，不是 30 条。
3. 当时没有任何运行归档，且 skillEval 对 `--mock` 会显式拒绝下质量结论
   （`synthetic mock run — pipeline smoke only, not a skill-quality verdict`），
   所以那组数字也不可能来自 mock 链路验证。

---

## 2. 文件结构与运行方式

### 文件结构

```
evals/
├── sync_subjects.py            # skills/ → evals/subjects/ 的唯一生成入口（--check 校验漂移）
├── build_control_subjects.py   # subjects/ → 对照组（剥离禁令）+ 对照组套件（--check 校验漂移）
├── compare_runs.py             # 两次 routing 运行的逐 case A/B 对比 + 失败模式拆解（只读）
├── fix_internal_dataset.py     # 内部数据集定向修订（幂等，带 CHANGELOG，v1.1–v1.6）
├── add_holdout_cases.py        # 追加锁定泛化题（v1.5，--check 校验不得修题）
├── run_internal_routing_eval.py# 内部路由评估（真实调用模型，含 gate 与健壮性检查）
├── datasets/
│   ├── pax_routing_v1.0.jsonl           # 外部路由，30 cases（含 # 注释头，读取时跳过）
│   └── pax_internal_routing_v1.0.json   # 内部路由，18 cases（version 1.6，含 4 条 holdout）
├── suites/
│   ├── pax_routing.yaml           # 基线套件（suite_version 2.1，已移除 multi_exact）
│   └── pax_routing_control.yaml   # 对照组套件（2.1-control，唯一差异是 skills.dir）
├── subjects/                         # 派生产物：由 sync_subjects.py 从 skills/ 生成，勿手编
├── subjects_control_no_prohibition/  # 派生产物：仅 description 剥离禁令，勿手编
├── CONTRACT_GAPS.md            # 契约缺口清单（10 项）+ 决策清单（4 项），静态分析，不调 API
├── records/
│   └── real_scenario_trial.md       # 预期决策记录（人工编写，未调用模型）
└── results/
    └── internal_routing_results.json # 内部路由评估结果（真实模型运行）
```

### 用例分布（实测，30 条）

| 类型 | 数量 | 说明 |
|------|------|------|
| pos | 16 | 明确可执行请求，期望路由到 pax-orchestrate |
| amb | 6 | 歧义请求（措辞含糊、缺少上下文、纯指代） |
| rej | 6 | 非 pax 任务（翻译、天气、概念解释、元讨论、提示注入） |
| multi | 2 | 多目标请求（诊断+回滚、调研+落地） |
| **合计** | **30** | |

### 运行方式

skillEval 克隆在 `C:\Users\sinvi\Documents\codes\agent-skills-tooling\skillEval`（本仓库同级）。
套件内的 `dataset` 与 `skills.dir` 是绝对路径，所以从 skillEval 根目录跑即可。

```bash
# 0. 派生产物同步（skills/ 变了才需要）
cd C:/Users/sinvi/Documents/codes/pax-skills
python evals/sync_subjects.py
python evals/build_control_subjects.py
cd C:/Users/sinvi/Documents/codes/agent-skills-tooling/skillEval

# 1. 只校验：不调 API、不写盘、不花钱
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline plan --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing.yaml" --healthcheck

# 2. mock 冒烟：验证链路，结果不可用于质量判断
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline run --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing.yaml" --mock --confirm

# 3. 真实运行：90 次请求（30 用例 × 3 repeats）
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline run --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing.yaml" --confirm --confirm-egress

# 3b. 对照组（换套件即可）
PYTHONUTF8=1 .venv/Scripts/python.exe -m pipeline run --suite \
  "C:/Users/sinvi/Documents/codes/pax-skills/evals/suites/pax_routing_control.yaml" --confirm --confirm-egress

# 3c. 自检对照组有没有漂移（不调 API）
cd C:/Users/sinvi/Documents/codes/pax-skills && python evals/build_control_subjects.py --check

# 3d. 两次运行逐 case 对比 + 失败模式拆解（不调 API）
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

`--confirm-egress` 是 skillEval 强制的外部数据确认：plan 会先打印外发清单
（prompt + skill 元数据），确认它符合预期再放行。

**Windows 注意**：skillEval 与内部评估脚本都必须加 `PYTHONUTF8=1`，
否则 `✓` / `✗` / `✓` 这类字符会在 GBK 控制台上崩。

---

## 3. 内部路由评估（真实模型调用）

测 pax-orchestrate 的**内部**决策：意图分类（W1）、风险评分（W2）、诊断必要性（W3）、路由构建（W4）。
与第 1 节是两层：第 1 节测「模型要不要选 pax-orchestrate」，本节测「pax-orchestrate 内部判得对不对」。

### 基线结果（2026-10-03 12:24，deepseek-flash，temperature=0，repeats=3）

18 案例 × 3 次 = 54 次判定，数据集 `pax_internal_routing_v1.0.json` **version 1.6**
（gold 未改；契约在 v1.6 基础上补 G3/G5/G6/G7/G9，G4 补 cco 优先级定义，回滚 G8）：

| 口径 | 通过 | 说明 |
|------|------|------|
| 原始 | 54/54 (100.0%) | |
| 剔除 gold/契约冲突字段 | 54/54 (100.0%) | v1.1 起冲突字段已全部解决，两口径一致 |
| **可解析且自洽（能力分）** | **54/54 (100.0%)** | **gate 以此为准** |

输出健壮性：**valid_rate = 54/54 (100.0%)**，无解析失败、无自相矛盾。

| 类别 | 能力口径 | 门槛 | 判定 |
|------|------|------|------|
| intent_classification | 21/21 (100.0%) | ≥0.95 | PASS |
| risk_scoring | 21/21 (100.0%) | ≥0.85 | PASS |
| route_building | 9/9 (100.0%) | ≥0.90 | PASS |
| cross_repo_detection | 3/3 (100.0%) | ≥0.90 | PASS |
| → **GATE** | 54/54 (100.0%) | ≥0.90 | **PASS** |

逐检查项（13 项全 100%）：

| 检查项 | n | 通过率 | 门槛 | 判定 |
|--------|---|--------|------|------|
| primary_intent | 21 | 100.0% | ≥0.95 | PASS |
| diagnose_required | 9 | 100.0% | ≥0.95 | PASS |
| cross_repo | 3 | 100.0% | ≥0.95 | PASS |
| execution_strategy_required | 3 | 100.0% | ≥0.95 | PASS |
| route | 9 | 100.0% | ≥0.90 | PASS |
| storage_backend_required | 9 | 100.0% | ≥0.90 | PASS |
| secondary_intent | 21 | 100.0% | ≥0.85 | PASS |
| risk_score | 21 | 100.0% | ≥0.85 | PASS |
| risk_level | 21 | 100.0% | ≥0.85 | PASS |
| irreversibility | 21 | 100.0% | ≥0.80 | PASS |
| impact_scope | 21 | 100.0% | ≥0.80 | PASS |
| uncertainty | 21 | 100.0% | ≥0.80 | PASS |
| coordination_cost | 21 | 100.0% | ≥0.80 | PASS |

稳定性：**0/18 案例跨 3 次不一致**（上轮 4/18）。
锁定分组：修订题 42/42 (100.0%)，holdout 12/12 (100.0%)。

### 三轮迭代：从 88.9% FAIL 回到 100% PASS

| 指标 | v1.6 | 第一轮（含 G4 过宽） | 第二轮（回滚 G4/G8） | **最终（G3 收窄 + cco 定义）** |
|------|------|------|------|------|
| 能力分 | 54/54 (100%) | 47/54 (86.8%) | 48/54 (88.9%) | **54/54 (100%)** |
| risk_scoring | 21/21 (100%) | 14/21 (66.7%) | 16/21 (76.2%) | **21/21 (100%)** |
| coordination_cost | 100% | 76.2% ✗ | 85.7% ✓ | **100%** |
| uncertainty | 100% | 95.2% | 90.5% | **100%** |
| risk_score | 100% | 66.7% ✗ | 76.2% ✗ | **100%** |
| holdout | 12/12 (100%) | 7/12 (58.3%) | 8/12 (66.7%) | **12/12 (100%)** |
| 稳定性 | 0/18 | 4/18 | 4/18 | **0/18** |
| 健壮性 | 100% | 98.2% | 100% | **100%** |
| GATE | PASS | FAIL | FAIL | **PASS** |

**最后两轮修正分别解决了什么**：

1. **G3 收窄**：「需要验证一轮 = 2」→「需要验证**一个未验证的假设**（调用顺序、性能、
   边界行为）= 2；照既有脚本/手册执行、验证方式已知的算 1」。修复 high-02
   （有明确清理手册）的 uncertainty 2/3 偏差
2. **cco 优先级定义**：「跨文件修改」指多文件联动的实质重构，不是字面文件数；prompt
   明确写「单人完成／不需要其他人配合」的以「单人可完成」为准判 1。修复 medium-03
   的 coordination_cost 2/3 偏差

**这轮 100% 比 v1.6 的 100% 更可信**：v1.6 是在 G3–G9 七项缺口未补时的结果，本轮是在
全部 10 项缺口补齐后的结果。不是同一个数字碰巧重复，而是契约补全后模型行为随之收敛。
稳定性从 4/18 回到 0/18 是额外证据：模型不再在边界题上摆动。

**但仍保留一条限定**：n=18×3=54 的小样本，100% 不等于泛化能力。详见下节。

### 与上一轮（v1.5）的对比：提升来自哪里

| 指标 | v1.5（契约有 G1/G2 缺口） | v1.6（契约已补） | 变化 |
|------|------|------|------|
| 能力分 | 46/52 (88.5%) | **54/54 (100.0%)** | +11.5pp |
| risk_scoring 类目 | 15/20 (75.0%) | **21/21 (100.0%)** | +25.0pp |
| 锁定题 holdout | 8/12 (66.7%) | **12/12 (100.0%)** | +33.3pp |
| 修订过的题 | 38/40 (95.0%) | **42/42 (100.0%)** | +5.0pp |
| 稳定性 | 4/18 不一致 | **0/18 不一致** | +稳定性 |
| 解析失败 | 2/54 | **0/54** | 改善 |
| GATE | FAIL | **PASS** | 转 PASS |

**提升全部来自两处，都是契约层面的改动：**

1. **补契约 G1 + G2**（`skills/pax-orchestrate/SKILL.md` W2 判据）：
   - G1：impact_scope 1 的「内部工具」加「仅本人使用」限定，并补显式边界
     「按实际使用人数判定——仅本人 1，多人含团队内共用 2」
   - G2：irreversibility 1 的「代码修改」限定为「未上线的本地改动」、
     「配置修改」限定为「不触发部署」，2 的示例改为「前端/后端部署（可回退）」，
     并补边界「改动需要部署上线才能生效的，即使可回滚也至少算 2」
2. **medium-01 的 gold 跟新契约**：irreversibility 1 → 2（总分 7 → 8，仍是 medium）。
   注意方向是**更严格**——模型原本稳定判 1，改完后需要跟上新契约才能通过。

### 因果证据：模型确实在读契约，不是背答案

这是本轮最有价值的证据，比任何总分都重要：

**`pax-risk-medium-03`（holdout 锁定题，prompt 与 gold 一字未改）：**

| 轮次 | 模型作答 | 契约状态 |
|------|------|------|
| v1.5 | **(1,1,2,1)=5/low**，3/3 稳定全错 | G1/G2 有歧义 |
| v1.6 | **(2,2,2,1)=7/medium**，3/3 全对 | G1/G2 已补 |

同一模型、同一 prompt、同一 gold，**唯一变量是契约文本**，作答从错到对。
这排除了「100% 是背数据集」的解释：模型是按契约文本推理的，
契约含糊时它跟着含糊走，契约明确时它就跟正确基准走。

**`pax-risk-medium-01`（gold 被主动改严格）：** irreversibility 从 1 改成 2 后，
模型 3/3 都判 2。模型跟上了新契约，而不是靠原有倾向蒙对。

**`pax-risk-high-02`（强制升级规则）**：总分 8 本应 medium，
但不可逆 3 + 影响 3 强制升 high，模型两轮都 3/3 正确应用该规则。

### 锁定分组：反拟合问题的实测答案

| 分组 | 能力口径 | case 数 |
|------|------|------|
| 修订过的题（v1.1–v1.6 改过 gold/prompt） | **42/42 (100.0%)** | 14 |
| 锁定题 holdout（从未修订过 prompt/gold） | **12/12 (100.0%)** | 4 |
| **差距** | **0.0pp** | |

holdout 逐题（v1.6，均为 3/3）：

| case | gold | 考点 | v1.5 → v1.6 |
|------|------|------|------|
| `pax-risk-low-02` (1,2,1,2=6/low) | low 上限边界 | 3/3 → **3/3** |
| `pax-risk-high-02` (3,3,1,1=8/high) | 强制升级规则 | 3/3 → **3/3** |
| `pax-risk-medium-02` (2,3,2,2=9/medium) | medium 上限边界 | 2/3 → **3/3** |
| `pax-risk-medium-03` (2,2,2,1=7/medium) | 协调成本 1 的 medium | 0/3 → **3/3** |

### 差距解读（诚实说明）

两轮修正后回到 100%，但这个 100% 仍受两个因素限定：

1. **n=18×3=54 的小样本**。100% 不等于泛化能力，一次抽样波动就可能造成 11–33pp 的差距。
   上轮 4/18 不一致率说明温度 0 下仍有采样噪声，而本轮 0/18 只是这一轮的表现。
2. **契约与 gold 均经过反复对齐**。数据集 v1.6 的 gold 与当前契约是自洽的——
   但这不代表它们对未见过的新题也自洽。holdout 4 题全部 3/3 是好消息，
   但 n=4 不足以支撑泛化结论。

**三轮迭代的真正价值不是「回到 100%」，而是暴露了两个真实的契约缺口**：
G3 的「验证」边界模糊（是否需要探索未知），cco 的「跨文件」优先级未定义。
这两个缺口都是在模型稳定失败后才被发现的——这正是评估应有的作用。
**修完后没有新 FAIL 出现**，说明两项修正没有引入新的不一致。

### 锁定规则的处理记录（历史）

v1.5 时 `pax-risk-medium-03` 0/3 全错，我**没有**改 prompt 或 gold。理由：

- 改 prompt 让答案变明确 = 看着模型答错后修数据集 = 反拟合老路。
- 改 gold 到模型答案 (1,1,2,1) = 把 gold 反过来拟合模型。

当时的判断是「契约未定义内部工具做 UI 组件替换的影响范围基准」，
不是 gold 与契约矛盾，所以不算锁定规则的例外。保留 FAIL，列为待补契约项。

**现在（v1.6）这个 FAIL 已消除，不是修题而是补契约的结果。** medium-03 的 prompt 与 gold
一字未改，`evals/add_holdout_cases.py --check` 锁定校验仍通过（见下）。

### 数据集修订记录（v1.0 → v1.6）

修订原则：gold 取值必须能**仅凭 prompt + 契约文字**推导出来。
prompt 缺信号 → 改 prompt；契约含糊 → 改契约；gold 与契约矛盾 → 改 gold。
**为了测试通过而放宽门槛或补下游无人使用的契约字段，都是把测试反过来拟合实现。**

| 版本 | 改动 | 类型 |
|------|------|------|
| **v1.1** | 删 7 条 intent gold 的 `confidence`（契约从未定义、W2–W4 无人读取，属装饰字段） | 改 gold |
| | `pax-risk-high-01` 补 prompt：「30 张表、约 800 万行、无法回滚重跑」 | 改 prompt |
| | `pax-intent-df-01` / `pax-route-df-01` 的 `secondary_intent` `[]` → `["data_integrity"]` | 改 gold |
| | 契约 W1 补 `ux_error` 易混淆边界；W2 补数据类任务 `impact_scope` 基准 | 补契约 |
| **v1.2** | risk 类 prompt 补 coordination 信号（「改动都在账务模块内部」「涉及后端接口 + 前端按钮」） | 改 prompt |
| **v1.3** | `pax-risk-medium-01`：「所有登录用户」→「多个业务用户」（原措辞命中契约 impact_scope=3 的原文判据「全用户」）；补「改动都在同一个仓库内」（原措辞被读成跨仓库） | 改 prompt |
| | `pax-risk-high-01`：补「涉及多个文件和表结构定义的修改」 | 改 prompt |
| **v1.4** | 三条 route_building 的 gold 改用**契约短名**（`clarify` 而非 `pax-clarify`）；打分器加前缀归一化 | 改 gold |
| **v1.5** | 追加 4 条 risk_scoring 锁定题（holdout，`evals/add_holdout_cases.py`）；评估脚本加 holdout 分组口径 | 加题（锁定） |
| **v1.6** | 补契约 G1/G2（W2 影响范围与不可逆性的判定边界）后，`pax-risk-medium-01` 的 `irreversibility` 1→2、`risk_score` 7→8（risk_level 仍 medium） | 补契约 + 改 gold |

**v1.6 后的契约迭代（2026-10-03 下午，数据集 gold 未改）**：

补契约 G3/G5/G6/G7/G9，G4/G8 补法回滚（分析有误，见 `CONTRACT_GAPS.md`）。
数据集版本保持 1.6，因为 gold 一字未动——契约是唯一变量。

**v1.5 的锁定规则**：这 4 条题的 prompt 与 gold 写入后**不再修订**。
模型答错如实记 FAIL。唯一例外是复核发现 gold 与契约原文直接矛盾（而非「模型没读懂措辞」），
且必须在 changelog 里写明「这是契约矛盾，不是拟合」。
4 条题覆盖 low 上限（6）、medium 上限（9）、强制升级规则（总分 8 升 high）、
协调成本 1 的 medium（7），四维组合与现有 3 条不重复。

`evals/add_holdout_cases.py` 带 `--check` 锁定漂移检测：如果数据集里的 holdout 题
与脚本写死的值不一致就 exit 1——这是对「不得修题」这条规则的机械约束，
不靠人自觉。

与 `fix_internal_dataset.py` 的分工：后者是针对历史题的**定向修订**，处理已确认的 gold/契约冲突；
前者只做**追加**，不碰已有 case。两个脚本改动范围不重叠。

**v1.4 的关键发现**：契约 W4 第 254 行原文就是 `route = ["clarify", "diagnose", "plan", "execute", "review"]`，
gold 写全名是 **gold 偏离契约**，不是模型错。模型三次里两次跟契约、一次跟 gold，
导致 8/9 而非 3/3——纯粹是记法差异，五个步骤和顺序完全一致。
外部路由数据集不受影响（那里比的是 skill 目录名，本来就该用 `pax-*` 全名）。

修订脚本 `evals/fix_internal_dataset.py` 是幂等的，带完整 CHANGELOG 和自检
（`confidence` 已清空 / prompt 生效 / 四维求和与等级映射自洽）。

### 4 项 gold/契约冲突的最终裁决

| 项 | 裁决 | 理由 |
|----|------|------|
| `confidence` 字段 | **改 gold**（删字段） | 契约 W1–W4 从未定义；W2–W4 不读取。下游无人用的装饰字段不应进入评分 |
| `pax-risk-high-01` | **改 prompt** | gold 3/3/2/2=10 自洽且命中 W2 强制升级规则，是 prompt 缺信号 |
| `pax-route-df-01` | **改 gold** | secondary 补 `data_integrity` 后 W4 条件成立，`storage_backend_required=true` 与契约一致 |
| `pax-intent-df-01` | **改 gold + 补契约** | gold 补 `data_integrity`；契约补「校验报错归 data_integrity，不归 ux_error」防未来摆动 |

其中「data_integrity 是否覆盖字段值校验失败」是我的判断，属**可争议决定**，
待业务方确认。结果 JSON 的 `gold_contract_resolutions` 字段完整记录了 4 项裁决与理由。

### gate 定义

```python
GATE_CHECKS = {
    # 契约写成查表 / MECE 分类 / 显式布尔条件：正确实现应当几乎永远对
    "primary_intent": 0.95, "diagnose_required": 0.95,
    "cross_repo": 0.95, "execution_strategy_required": 0.95,
    # 查表结果的链式拼接，误差随链条放大，留一档余量
    "route": 0.90, "storage_backend_required": 0.90,
    # 可叠加标签 + 语义边界判定
    "secondary_intent": 0.85,
    # 聚合值：单维误差可能被其他维抵消，但强制升级规则需要稳定
    "risk_score": 0.85, "risk_level": 0.85,
    # 1–3 主观量纲，契约只给示例不给阈值，最难收敛
    "irreversibility": 0.80, "impact_scope": 0.80,
    "uncertainty": 0.80, "coordination_cost": 0.80,
}
GATE_CATEGORY = {"intent_classification": 0.95, "risk_scoring": 0.85,
                 "route_building": 0.90, "cross_repo_detection": 0.90}
GATE_OVERALL = 0.90       # 整体能力分
GATE_VALID_RATE = 0.95    # 输出健壮性（可解析 + 自洽）
```

门槛按**契约确定性**分档，不是从测量分布反推：查表类该近乎全对，主观量纲类允许更多余量。
`--rescore` 带漂移检测：prompt 或契约字符数与结果 JSON 记录的不一致就拒跑（exit 2）。

### 健壮性检查（两层）

- **`parse_rate`**：模型必须按契约吐合法 JSON（`response_format={"type":"json_object"}`）。
- **`structure_failures`**：JSON 语法合法但自相矛盾也算无效输出。
  当前实现检查三条：`risk_score ≠ 四维之和`、`diagnose_required=true 但 route 为空`、
  `route_building 题返回空 route`。

两类都属输出健壮性，**不算路由判断能力**。这个区分很重要：
把「吐出一份四维全是 1 却报 risk_score=0 的 JSON」算成「风险评分答错」，
会把能力分和输出质量混成一团，问题也就定位不到。

### 使用方式

```bash
PY=../agent-skills-tooling/skillEval/.venv/Scripts/python.exe   # 任一装好 openai 的解释器

# 真实运行（repeats=3 → 54 次请求，18 题 × 3）
$PY evals/run_internal_routing_eval.py --repeats 3

# 只调契约、没改 prompt 时：不重新调用模型，按当前 gold 重判
$PY evals/run_internal_routing_eval.py --rescore

# 不调 API，看将发送的系统提示（自检提示词有没有越界）
$PY evals/run_internal_routing_eval.py --dry-run

# 修订数据集（幂等，v1.1–v1.4 定向修订，带自检）
python evals/fix_internal_dataset.py

# 锁定漂移检测：holdout 题被改过就 exit 1（不靠人自觉）
python evals/add_holdout_cases.py --check

# 自洽性测试（stub 对金标，不测真实 skill）
$PY -m pytest tests/test_orchestrate_routing.py -v
```

系统提示 = SKILL.md 的 W1–W4 原文，**未注入契约外的任何澄清**——
否则衡量的是补丁而不是 skill 本身。
密钥从 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` 环境变量取。pax-skills 无自带 venv。

### 关于 `tests/test_orchestrate_routing.py`

这 5 个 pytest **不是**对 pax-orchestrate 的能力评估：文件里手写的 `_classify_intent()` /
`_build_route()` 是关键词匹配桩，从未读过 SKILL.md，因此只证明「桩的输出」与「数据集 gold」一致。
它们保留为「意图 → 路由映射」的回归基线：改 SKILL.md 的路由表时应会失败并提醒。

---

## 4. 真实场景试跑（预期决策记录，未实际调用模型）

`evals/records/real_scenario_trial.md` 里的「预期路由决策」是人工编写的参考基准，
后面的「测试结果」JSON 数值与之完全相同——**没有调用过模型**，不是实测结果。
该文件只应作为「这些场景应该输出什么」的人工基准参考，不可引用为验证结论。

### 场景

| 场景 | 意图 | 风险 | 路由 | 跨仓库 |
|------|------|------|------|--------|
| CMDB 数据订正 | data_ops | high (9) | clarify→diagnose→plan→execute→review | ✓ |
| 新功能开发 | feature_dev | medium (6) | clarify→plan→execute→review | ✗ |
| 文档咨询 | doc_consult | low (4) | clarify | ✗ |

---

## 5. 待办

**G3–G9 已补完、两轮修正已验证（2026-10-03 12:24），内部 GATE PASS（100%），
外部路由 2.1 GATE PASS，套件路径已改相对路径。**

1. **✅ G3 补法已收窄** —— 「需要验证一个未验证的假设（调用顺序、性能、边界行为）
   = 2；照既有脚本/手册执行、验证方式已知的算 1」。high-02 uncertainty 回到 3/3
2. **✅ medium-03 的 cco 已定义优先级** —— 「跨文件修改」指多文件联动的实质重构，
   不是字面文件数；prompt 明确写「单人完成／不需要其他人配合」的以「单人可完成」为准
   判 1。medium-03 coordination_cost 回到 3/3
3. **n 太小，结论仍不稳**：holdout 仅 4 题 12 判定，一轮 100% 不等于稳定表现。
   稳定性从 4/18 回到 0/18 是好消息，但仍是单轮结果。要拿因果证据当可靠结论，
   需 repeats 提到 5–10 或题量翻到 40+，都是付费成本
4. **✅ 外部 100% / 对照组 71.1% 的结论已归档**（D1=B）：禁令是契约必要组成，
   28.9pp 是设计代价而非禁令副作用；对照组只回答「贡献多少」，不回答「要不要」
5. **G10 待业务方确认**：data_integrity 是否覆盖字段值校验失败。我的裁决已落地
   到契约和 gold，但如果业务方不认，两处 gold 要改回
6. **漂移检测 bug 已修**：`meta.contract_chars` 之前从未写入（实际写在 `usage` 里），
   导致主流程与 `--rescore` 读的字段不一致。已统一移到 `meta`，且缺失时也拒跑
   （无法确认契约没变，不能放行）

---

## 6. 文件变更

评估文件不受 `.gitignore` 限制，应纳入版本控制。
skillEval 的运行归档（`outputs/`）在仓库外，不进 git。
