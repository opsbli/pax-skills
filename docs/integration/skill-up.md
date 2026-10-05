# skill-up 集成建议

## 概述

skill-up 是一个技能升级框架，用于评估 agent 学习新技能的能力。pax 家族的 pax-learn 可以集成 skill-up 来评估学习能力和知识图谱构建。

## 前置条件

- [ ] 需要安装 Docker（本机已有 28.5.1）
- [ ] 需要定义学习任务模板
- [ ] 需要设置评估标准（学习速度、知识保留、迁移能力）

## 集成方案

### 方案 A：端到端评估（推荐）

1. 在 `evals/datasets/` 下创建学习任务数据集
2. 使用 pax-learn 执行学习任务
3. 通过 skill-up 评分

```bash
# 示例
docker run -v $(pwd)/evals:/evals skill-up run --dataset /evals/pax-learn.yaml
```

### 方案 B：集成到 CI

1. 在 `.github/workflows/pax-ci.yml` 中添加 skill-up 评估 job
2. 仅在 push 时运行，不阻塞 PR

## 风险

- skill-up 依赖 Docker，CI 环境可能不支持
- 需要维护学习任务数据集

## 建议

优先使用方案 A（本地评估），待 CI 环境支持后再集成到流水线。

## 参考

- skill-up 文档：https://github.com/your-org/skill-up
- pax-learn SKILL.md：`skills/pax-learn/SKILL.md`