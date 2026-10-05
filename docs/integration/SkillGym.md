# SkillGym 集成建议

## 概述

SkillGym 是一个技能评估框架，用于评估 agent 在特定任务中的表现。pax 家族可以集成 SkillGym 来对单 skill 进行端到端评估。

## 前置条件

- [ ] pax 家族已有 17 个 skill 无单 skill 评估覆盖
- [ ] SkillGym 需要定义任务模板、评分标准、测试用例
- [ ] 需要与 pax 的 snapshot 机制对接

## 集成方案

### 方案 A：轻量集成（推荐）

1. 在 `evals/datasets/` 下为每个 skill 创建 SkillGym 兼容的任务定义
2. 使用 pax 的 `scripts/run_skill_eval.py` 作为 runner
3. 通过 SkillGym 的 CLI 调用 runner

```bash
# 示例
skillgym run --task evals/skillgym/pax-plan/tasks.yaml
```

### 方案 B：深度集成

1. 将 pax 的 skill 执行逻辑封装为 SkillGym 的 agent
2. 使用 SkillGym 的完整评估流水线
3. 需要实现 SkillGym 的 agent interface

## 风险

- SkillGym 的评分标准与 pax 的能力分门槛（≥0.90）可能不一致
- 需要维护两套评估体系

## 建议

优先使用方案 A（轻量集成），利用 pax 现有的 runner 和数据集，仅借用 SkillGym 的任务定义格式。

## 参考

- SkillGym 文档：https://github.com/your-org/skillgym
- pax 评估目录：`evals/`