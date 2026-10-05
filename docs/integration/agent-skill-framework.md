# agent-skill-framework 集成建议

## 概述

agent-skill-framework 是一个 agent 技能框架，用于管理和执行 agent 技能。pax 家族可以与 agent-skill-framework 集成，实现技能注册、发现和调用。

## 前置条件

- [ ] 需要接入 Agnes AI API（当前未接入）
- [ ] 需要将 pax skill 转换为 agent-skill-framework 格式
- [ ] 需要设置 API key 和认证

## 集成方案

### 方案 A：注册 pax skill（推荐）

1. 将 pax 的 SKILL.md 转换为 agent-skill-framework 的 skill definition
2. 注册到 agent-skill-framework
3. 通过 API 调用

```python
# 示例
from agent_skill_framework import AgentSkill

pax_clarify = AgentSkill.from_markdown("skills/pax-clarify/SKILL.md")
pax_clarify.register()
```

### 方案 B：使用 pax 作为 agent-skill-framework 的 backend

1. 将 pax-orchestrate 封装为 agent-skill-framework 的 router
2. 通过 pax 路由调用其他 skill

## 风险

- 需要 Agnes AI API，当前未接入
- 需要维护两套 skill 定义格式

## 建议

由于需要 Agnes AI API 接入，建议暂缓集成，待 API 可用后再评估。

## 参考

- agent-skill-framework 文档：https://github.com/your-org/agent-skill-framework
- pax-orchestrate SKILL.md：`skills/pax-orchestrate/SKILL.md`