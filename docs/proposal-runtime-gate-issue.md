# [提案] 运行时门禁：把「先走 pax-orchestrate」从软约束升级为写/编译/git 的硬前置

> 状态：proposal（待评审）
> 归属：Proma 运行时（`agent-runtime.cjs` / `main.cjs`）
> 关联：pax-family（github.com/opsbli/pax-skills）
> 类型：feat / enhancement
> 可直接粘贴为 GitHub Issue 使用；详细契约见同仓库 `docs/runtime-gate-requirement.md`。

---

## 摘要

pax-family 通过项目根 `AGENTS.md` 要求 Agent「对任何用户请求，MUST 先经过 L0 编排入口
（pax-orchestrate），NEVER 直接执行」。实测（2026-10-09，xls 会话 7129e309）证明：这份
AGENTS.md **已被 Proma 正常注入 system prompt**，但 Agent 面对"看似直读直改"的修复任务时仍
**无视该 MUST 条款**，直接改代码并提交，全程未调编排、未产出快照。

结论：`project_instructions` 注入是「信息注入」、不是「门禁执行」。要把编排变成真正执行的
前置条件，需要 Proma 运行时在工具调用层提供**命令式门禁**。

## 问题复现（最小）

1. 项目 `cmp-preview` 已接入 pax-family（`D:\workspaces\cmp-preview\AGENTS.md` 含强制规则）。
2. 发起任务：「xls 预览 sheet 没有分页，帮我修复」。
3. 当前行为：Agent 直接读代码→改→编译→提交 `c1e08d5d`，**未调用 pax-orchestrate**、未生成
   `.pax/plan/pax-snapshot.yaml`。
4. 期望行为：在写/编译/git 之前被运行时拦截，提示先走编排；或用户显式选择跳过。

## 建议实现（挂载点）

利用 Proma 已有扩展点（`beforeToolCall` / `canUseTool`）：

| 项 | 说明 |
|---|---|
| 作用对象 | 已接入 pax-family 项目的**写文件 / 编译 / 构建 / git** 动作 |
| 触发条件 | `projectRoot` 存在 `.pax/project-profile.json` 或含 `pax-family 强制规则` 的 `AGENTS.md`；任务属家族意图（非 doc_consult）；动作非只读 |
| 放行条件 | 命中任一即放行：① 已达成编排（本轮 `pax-snapshot.yaml` 存在或本会话已调 orchestrate）；② 用户显式选择跳过；③ 未接入/非家族意图/只读；④ 门禁自身故障（fail-open） |
| 拦截提示 | 「该项目已接入 pax-family。当前任务尚未经过 L0 编排入口，禁止在达成编排前直接执行写/编译/git。请先调用 pax-orchestrate 产出任务快照。若确需跳过，请选择跳过编排继续。」 |
| 跳过通道 | 用户主动选择，不由模型自行决定；留痕便于审计 |
| 安全 | fail-open（判定失败默认放行 + 告警），避免误判锁死开发 |

## 验收标准

- [ ] 已接入家族项目：未编排即写/编译/git 被拦截并给出提示
- [ ] 达成编排后同类动作放行；未接入项目不受影响
- [ ] 用户显式跳过后可继续且留痕
- [ ] 非家族意图 / 只读 / doc_consult 不触发
- [ ] 门禁异常时 fail-open（放行 + 告警），不中断开发

## 补充信息

- 详细契约：`docs/runtime-gate-requirement.md`（触发/放行/边界/验收完整版）
- 评估工具：`evals/datasets/instruction-compliance/ic_v1.0.json` + `evals/run_ic_eval.py`
  （用于量化强弱措辞的遵守率；需真实模型 API 运行）
- 说明：pax-skills 是纯 CLI（pax-forge），无运行时拦截能力，本体需 Proma 运行时接入本契约。

---

> 附注：若本仓库不是 Proma 主项目，本文件作为可粘贴的 issue 正文产出；确认 target repo 后可直接提交。
