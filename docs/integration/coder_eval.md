# coder_eval 集成建议

## 概述

coder_eval 是一个代码生成评估框架，用于评估 agent 在编码任务中的表现。pax 家族的 pax-execute 和 pax-worker-implement 可以集成 coder_eval 来评估代码生成能力。

## 前置条件

- [ ] 需要安装 `@anthropic-ai/claude-code` 或等效的 coding agent
- [ ] 需要定义编码任务模板（bug fix、feature、refactor）
- [ ] 需要设置评分标准（测试通过率、代码质量、安全）

## 集成方案

### 方案 A：端到端评估（推荐）

1. 在 `evals/datasets/` 下创建编码任务数据集
2. 使用 pax-execute 执行编码任务
3. 通过 coder_eval 评分

```bash
# 示例
coder_eval run --dataset evals/datasets/pax-execute-coding.yaml
```

### 方案 B：单独评估

1. 使用 coder_eval 直接评估 pax-worker-implement
2. 不依赖 pax-execute

## 风险

- 本机缺少 `@anthropic-ai/claude-code`，无法执行
- 需要维护测试用例和评分标准

## 建议

由于本机缺少必要依赖，建议暂缓集成，待依赖可用后再评估。

## 参考

- coder_eval 文档：https://github.com/your-org/coder-eval
- pax-execute SKILL.md：`skills/pax-execute/SKILL.md`