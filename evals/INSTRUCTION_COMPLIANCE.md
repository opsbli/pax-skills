# 指令遵守评估归档（Instruction Compliance Eval）

> 2026-10-09 · 模型 `deepseek-chat`（deepseek 官方，OpenAI 兼容）· 注入真实 `cmp-preview/AGENTS.md`
> 目的：量化「AGENTS.md 被注入后，模型是否把 pax-orchestrate 作为第一步」——回答用户质疑
> 「AGENTS.md 为什么没约束走 pax-family 工作流」。

## 背景结论

经解包 Proma 运行时核对，`cmp-preview/AGENTS.md` 早已被 `<project_instructions>` 注入
system prompt，但 xls 会话（7129e309）仍无视「先走编排」直接改代码。为判断「注入是否有效」，
做了四版受控评估。

## 工具与数据集

- 数据集：`evals/datasets/instruction-compliance/ic_v1.0.json`（10 条真实修复/开发任务）
- 弱/强措辞模板内嵌于数据集 `templates`
- Runner：
  - `evals/run_ic_eval.py`            —— v1 服从性
  - `evals/run_ic_trigger_eval.py`    —— v2 表态式触发
  - `evals/run_ic_exec_eval.py`       —— v3 执行式触发（工具集选第一步）
  - `evals/run_ic_distract_eval.py`   —— v4 注意力稀释（噪声 + 位置差异）
- 均支持 `--dry-run`；真实运行需 `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`

## 结果

| 版本 | 测什么 | 结果 |
|---|---|---|
| v1 服从性 | 明示第一步调编排，模型是否服从 | 10/10（weak 与 strong 均 100%） |
| v2 表态触发 | 注入 AGENTS.md，让模型“说明第一步” | 10/10 自发提到编排 |
| v3 执行触发 | 注入 AGENTS.md + 工具集，选第一步工具 | 10/10 首选 `pax_orchestrate` |
| v4 注意力稀释 | 噪声稀释 + AGENTS.md 位置（middle/back） | 10/10 仍首选编排 |

结果 JSON 存于 `evals/results/instruction_compliance_*.json`。

## 解读（关键边界）

- **受控条件下**：AGENTS.md 一旦被模型完整看到，其对「先走编排」的遵守与触发意愿稳定在 100%。
  这**反驳了“文本约束必然失效”**的担忧。
- **未覆盖的真实条件**：受控评估是“prompt 内让模型决策第一步”，模型有余裕展示规范响应；
  真实事故发生在**多轮实际执行 + 超长 system prompt** 中，模型自由调用工具、注意力被稀释，
  可能直接钻进代码——本次 v4 已用噪声模拟部分稀释，但仍非完整多轮执行复现。

## 对治理的意义

1. 不是「AGENTS.md 没注入」导致的失效——证据表明注入正常。
2. 硬门禁（Issue #1）定位为**防漏 / 兜底**，而不是“唯一依赖”：解决真实自由长上下文执行中
   “偶尔不自发先走编排”的残余风险。
3. 四版评估基础设施可复跑，便于后续换模型/换措辞再测。

## 复跑命令示例

```bash
# v1
DEEPSEEK_API_KEY=... DEEPSEEK_BASE_URL=https://api.deepseek.com \
  INTERNAL_EVAL_MODEL=deepseek-chat \
  .venv/Scripts/python.exe evals/run_ic_eval.py
# v2 / v3
.venv/Scripts/python.exe evals/run_ic_trigger_eval.py --agents-md /path/AGENTS.md
.venv/Scripts/python.exe evals/run_ic_exec_eval.py --agents-md /path/AGENTS.md
# v4（位置对照）
.venv/Scripts/python.exe evals/run_ic_distract_eval.py --agents-md /path/AGENTS.md --agents-position middle
.venv/Scripts/python.exe evals/run_ic_distract_eval.py --agents-md /path/AGENTS.md --agents-position back
```
