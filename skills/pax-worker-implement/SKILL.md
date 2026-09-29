---
name: pax-worker-implement
description: >
  有界实现任务执行。L3 层工具适配，接口由上层定义；将有界的编码/编辑任务委托给固定 worker，在沙箱与无头模式下运行并返回 diff。
version: 0.1.0
family: pax
layer: L3
optional: true
requires_snapshot: true
---

# pax-worker-implement

## Execution Contract
- 前置门禁：调用方已定义任务边界与输入
- 未通过门禁：拒绝执行
- 版本检查：`pax-ops/versions.json`
- 沙箱：必须在 isolated FS / network 下运行
- 无头：不得依赖交互输入
- 边界：不得跨越调用方给定的任务范围
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界
- 做什么：将有界实现任务委托给固定 worker，产出变更 diff
- 不做什么：不做路由决策、不修改上层快照字段、不扩大任务范围

## 输入
- 必需：任务描述、约束、输入上下文、变更边界
- 可选：优先级、超时、期望测试清单

## 工作流
1. 沙箱准备（isolated FS / network）
2. 无头执行实现任务
3. 收集输出、日志、diff、退出码
4. 打包返回给调用方

## 输出契约
- 变更 diff、执行日志、退出码、测试结果

## 失败模式
- 任务超时 → kill 并返回 `partial`
- 沙箱失败 → 拒绝执行
- 变更超出给定边界 → 拒绝返回，附说明
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 任务超出 worker 能力 → 返回上游阶段请求重规划
