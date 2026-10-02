# pax-* 家族路由评估

本目录包含 pax-* 家族的两套评估工具：

1. **外部路由评估**（skillEval `routing_only`）：测「模型面对用户请求时选不选 pax-orchestrate」
2. **内部路由评估**（自研脚本，真实调用）：测「pax-orchestrate 内部的四步决策对不对」

两层合起来才能判断路由质量。两层的门槛性质不同，下文分别说明。

---

## 1. 外部路由评估

### 当前基线（2026-10-02，30 条用例）

| 项 | 值 |
|------|------|
| 模型 | `openai/deepseek-flash` @ `api.deepseek.com`，temperature=0 |
| 套件 | `pax_routing.yaml`，suite_version 2.0 |
| config_hash | `sha256:c3416c72d0d06f63` |
| 数据集 | `pax_routing_v1.0.jsonl`，**30 cases**（16 pos / 6 amb / 6 rej / 2 multi） |
| catalog | 18 个 pax skill，内容 hash 固化在 `config.snapshot.yaml` |
| 归档 | skillEval `outputs/pax_routing_v1.0__deepseek-flash__v1/20261002T201555925185+0800` |
| 工作量 | 90/90 turns 成功（30 × 3 repeats），0 错误 |

| 指标 | 门槛 | 实测 | 判定 |
|------|------|------|------|
| exact_set_match | ≥0.80 | **100.0%** | PASS |
| top1 | ≥0.85 | **100.0%** | PASS |
| no_skill_rejection | ≥0.90 | **100.0%**（18/18） | PASS |
| false_activation | ≤0.10 | **0.0%** | PASS |
| type_amb | ≥0.70 | **100.0%** | PASS |
| multi_exact | — | NaN（结构性 n/a，见下） | — |
| → **GATE** | | | **PASS** |

稳定性：跨 3 次 repeat **100.0% ± 0.0%**，flaky case **0 个**，pass@3 = pass^3 = 100%。
效率：1.37 ± 0.47 s / turn，1192 ± 60 tokens，0 tool calls（routing_only 预期）。

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

### 关于 `multi_exact` 为什么是 NaN

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
├── fix_internal_dataset.py     # 内部数据集修订脚本（幂等，带 CHANGELOG，1.0 → 1.4）
├── run_internal_routing_eval.py# 内部路由评估（真实调用模型，含 gate 与稳健性检查）
├── datasets/
│   ├── pax_routing_v1.0.jsonl           # 外部路由，30 cases（含 # 注释头，读取时跳过）
│   └── pax_internal_routing_v1.0.json   # 内部路由，14 cases（version 1.4）
├── suites/
│   ├── pax_routing.yaml           # 基线套件（suite_version 2.0）
│   └── pax_routing_control.yaml   # 对照组套件（2.0-control，唯一差异是 skills.dir）
├── subjects/                         # 派生产物：由 sync_subjects.py 从 skills/ 生成，勿手编
├── subjects_control_no_prohibition/  # 派生产物：仅 description 剥离禁令，勿手编
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

### 基线结果（2026-10-02，deepseek-flash，temperature=0，repeats=3）

14 案例 × 3 次 = 42 次判定，数据集 `pax_internal_routing_v1.0.json` **version 1.4**：

| 口径 | 通过 | 说明 |
|------|------|------|
| 原始 | 41/42 (97.6%) | 含 1 行自相矛盾输出 |
| 剔除 gold/契约冲突字段 | 41/42 (97.6%) | v1.1 起冲突字段已全部解决，两口径一致 |
| **可解析且自洽（能力分）** | **41/41 (100.0%)** | **gate 以此为准** |

输出健壮性：**valid_rate = 41/42 (97.6%)**，其中语法不可解析 0 次、自相矛盾 1 次
（`pax-risk-high-01` r2：四维都是 1 却报 `risk_score=0`，四维最小和是 4）。

| 类别 | 能力口径 | 门槛 | 判定 |
|------|------|------|------|
| intent_classification | 21/21 (100.0%) | ≥0.95 | PASS |
| risk_scoring | 8/8 (100.0%) | ≥0.85 | PASS |
| route_building | 9/9 (100.0%) | ≥0.90 | PASS |
| cross_repo_detection | 3/3 (100.0%) | ≥0.90 | PASS |
| → **GATE** | 41/41 (100.0%) | ≥0.90 | **PASS** |

逐检查项（13 项全部 PASS，门槛按契约确定性分档）：

| 检查项 | n | 通过率 | 门槛 |
|--------|---|--------|------|
| primary_intent | 21 | 100.0% | ≥0.95 |
| diagnose_required | 9 | 100.0% | ≥0.95 |
| cross_repo | 3 | 100.0% | ≥0.95 |
| execution_strategy_required | 3 | 100.0% | ≥0.95 |
| route | 9 | 100.0% | ≥0.90 |
| storage_backend_required | 9 | 100.0% | ≥0.90 |
| secondary_intent | 21 | 100.0% | ≥0.85 |
| risk_score | 8 | 100.0% | ≥0.85 |
| risk_level | 8 | 100.0% | ≥0.85 |
| irreversibility / impact_scope / uncertainty / coordination_cost | 8 | 各 100.0% | ≥0.80 |

稳定性：1/14 案例跨 3 次不一致（`pax-risk-high-01`）。
tokens：input 149,199 / output 40,910。

### 这个 100% 的可信度边界（必须一起读）

100% **不是无偏估计**。数据集从 v1.0 修订到 v1.4，共改过 **6 处 gold**，
其中至少 4 处是**观察模型答错之后才去核对契约、发现 gold 有问题**的。
也就是说，数据集已经在某种程度上被「反拟合」过模型行为了。

诚实的结论是：

- **契约明确且自洽的地方，模型确实全对**（primary_intent、diagnose_required、cross_repo、
  execution_strategy_required 各 21/21、9/9、3/3、3/3）。这部分是 v1.0 就成立的结论，
  不依赖任何后续修订。
- **1–3 主观量纲（四个 risk 维度）是契约实现最弱的部分**，但契约澄清 + gold 修正后
  已收敛到 8/8。要证明这不是拟合，需要**新写一条从未见过的 risk 题**来验证泛化。
- **n 很小**：risk 类每题 3 次判定，一次偏差就能移动 11–33pp。gate 是回归警报，
  不是质量证明。

### 数据集修订记录（v1.0 → v1.4）

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

# 真实运行（repeats=3 → 42 次请求）
$PY evals/run_internal_routing_eval.py --repeats 3

# 只调契约、没改 prompt 时：不重新调用模型，按当前 gold 重判
$PY evals/run_internal_routing_eval.py --rescore

# 不调 API，看将发送的系统提示（自检提示词有没有越界）
$PY evals/run_internal_routing_eval.py --dry-run

# 修订数据集（幂等，1.0 → 1.4，带自检）
python evals/fix_internal_dataset.py

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

1. **业务方定 2 项外部路由口径**（阻塞 gold 定形与发布判断）：
   - L1 skill 面对「看起来就是它的任务」时该不该被直选？（决定 `pax-pos-09` / `pax-pos-10` 的 gold）
   - 多目标/歧义请求是否允许一次选多个 skill？（决定 8 次 missing_entry 的归因）
2. **业务方确认 `data_integrity` 是否覆盖字段值校验失败**（内部路由 4 项裁决之一，我的判断）。
3. **新增从未见过的 risk 题**验证 1–3 主观量纲的泛化能力（当前 8/8 是在修订过的题上取得的）。
4. **门槛分辨率不足**：基线 100% 时 PASS/FAIL 无分辨率，需要更难的题集让基线落在 80–95%。

---

## 6. 文件变更

评估文件不受 `.gitignore` 限制，应纳入版本控制。
skillEval 的运行归档（`outputs/`）在仓库外，不进 git。
