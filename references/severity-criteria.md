# Severity 量化标准

`pax-diagnose` 输出的 `severity` 必须按以下标准评估。

## P0 —— 严重

**判断标准**（任一满足即 P0）：

- 核心流程完全不可用
- 影响所有用户
- 无临时规避手段
- 涉及安全（数据泄露、认证绕过、注入等）

**触发**：强制升级 `pax-council`，人工审批后方可进入 `pax-plan`。

## P1 —— 主要

**判断标准**（任一满足）：

- 核心流程部分不可用（有替代路径）
- 影响部分用户
- 存在临时规避手段

**触发**：正常走 `plan -> execute -> review`。

## P2 —— 次要

**判断标准**（任一满足）：

- 非核心流程部分不可用
- 影响少量用户
- 有明显规避手段

**触发**：可合并到常规迭代，走标准流程。

## 评估维度

`severity_rationale` 必须显式填写以下四项：

- `core_flow_broken`: 是否影响核心流程
- `affected_users`: all / most / some / few
- `workaround_available`: 是否有临时规避
- `security_relevant`: 是否涉及安全
