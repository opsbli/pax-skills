---
name: pax-clarify
description: >
  共识状态机、设计树维护、缺口检测、契约草稿。当需要澄清模糊需求、收敛共识或产出可冻结契约时使用。
version: 0.1.0
family: pax
layer: L1
optional: false
requires_snapshot: true
---

# pax-clarify

## Execution Contract
- 前置门禁：快照已初始化，`orchestration.question_strategy` 已确定
- 未通过门禁：拒绝启动，返回用户补齐信息
- 版本检查：`pax-ops/versions.json`
- 禁止在 `frontier` 非空时冻结契约或进入下一阶段
- 环境事实不得询问用户，必须调度 `pax-worker-*` 自动获取

## 职责边界
- 做什么：共识状态机、设计树维护、缺口检测、契约草稿
- 不做什么：不做任务分解、不执行动作、不产出执行日志、不做独立评审

## 输入
- 必需：`snapshot.orchestration`（含 `route`、`question_strategy`）
- 可选：历史快照、领域依赖映射、参考文档

## 工作流
1. 初始化设计树（从路由结果出发），节点标注 `depends_on` / `children`
2. 循环：
   - 计算前沿（frontier = 所有依赖已 settled 的未决节点）
   - 若 `question_strategy == batch`：一次性输出所有前沿问题，附推荐答案
   - 若 `question_strategy == one-by-one`：按优先级逐个提问，每次一个
   - 需要环境事实的问题，调度 `pax-worker-*` 自动获取，不询问用户
   - 记录用户答案，标记节点 `settled`，重塑设计树
   - 同步更新 `consensus.dimensions`
   - 检测剩余缺口 `gaps_remaining`
3. 终止条件：
   - `frontier == []`
   - 且所有 `required_precision` 维度达到 `confirmed` 或 `locked`
4. 产出契约草稿，等待用户确认后交由规划阶段

双引擎驱动：
- **设计树引擎**：负责逻辑完备性；维护 `depends_on` / `children` 与前沿
- **共识维度引擎**：负责风险适配精度；检测每个维度状态是否达到 `required_precision`

问题选择原则：
- 只问能改变行动的问题
- 优先"默认假设 + 风险标注"，而非开放式提问
- 阻塞性缺口必须问；优化性缺口给默认值；可后置缺口写入待办

## 输出契约
- `snapshot.consensus`（dimensions / gaps_remaining / settled_at）
- `snapshot.contract` 草稿，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 用户回答矛盾 → 标记冲突，请求澄清
- 用户疲劳 → 自动降级为 batch 模式，减少轮次
- 无法收敛 → 升级 `pax-council`
- 用户拒绝提供信息 → 使用保守默认值并标注风险

## 何时升级
- 无法收敛或高风险决策 → `pax-council`
- 需要环境事实 → `pax-worker-*`
- 需要独立评审 → `pax-review`
