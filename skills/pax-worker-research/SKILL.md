---
name: pax-worker-research
description: >
  有界研究任务执行。L3 层工具适配，接口由上层定义；将检索、抓取、只读探测等研究任务委托给固定 worker，在沙箱与无头模式下运行。
version: 0.1.0
family: pax
layer: L3
optional: true
requires_snapshot: true
---

# pax-worker-research

## Execution Contract
- 前置门禁：调用方已定义任务边界与输入
- 未通过门禁：拒绝执行
- 版本检查：`pax-ops/versions.json`
- 沙箱：必须在 isolated FS / network 下运行
- 无头：不得依赖交互输入
- 只读：不修改调用方快照字段
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：将有界研究/检索任务委托给固定 worker
- 不做什么：不做路由决策、不修改上层快照字段、不做写操作

## 输入
- 必需：任务描述、约束、输入上下文
- 可选：优先级、超时、检索源白名单

## 工作流
1. 沙箱准备（isolated FS / network）
2. 无头执行研究任务（检索 / 抓取 / 只读探测）
3. 收集输出、日志、引用来源
4. 打包返回给调用方（结果 + 置信度 + 出处）

## 输出契约
- 结构化结果、引用来源、执行日志、退出码

## 失败模式
- 任务超时 → kill 并返回 `partial`
- 沙箱失败 → 拒绝执行
- 检索源不可用 → 返回 `blocked`，附 `missing_information`
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 任务超出 worker 能力 → 返回上游阶段请求重规划
- 结果不确定度高 → 请求调用方补充上下文
