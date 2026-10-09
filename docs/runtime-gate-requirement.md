# 运行时门禁需求契约（Runtime Gate Requirement）

> 面向 Proma 运行时（app.asar 内 `agent-runtime.cjs` / `main.cjs`）的接入需求。
> 本文档描述了「当项目已接入 pax-family 时，如何把『必须先走编排』从软约束升级为运行时硬门禁」的
> 触发条件、放行条件、错误提示与用户跳过通道，以及相应的验收标准。
> 本文件只定义需求契约；是否/如何在 Proma 运行时实现，由 Proma 主项目侧决定。

---

## 1. 背景与问题

证据（2026-10-09 核实的 xls 会话 7129e309）：

- Proma 已把 `cmp-preview/AGENTS.md` 通过 `<project_instructions>` 注入 system prompt，其中明确写着
  「对任何用户请求，MUST 先经过 L0 编排入口，NEVER 直接执行」。
- 但 Agent 面对"xls 分页修复"这类看似直读直改的任务时，**无视了该 MUST 条款**，直接改代码并提交，
  全程未调用 `pax-orchestrate`、未产出 `.pax/plan/pax-snapshot.yaml`。
- 结论：`project_instructions` 是**信息注入**，不是**门禁执行**。文本约束对运行中模型无强制力。

因此需要在运行时增加**命令式门禁**，把"达成编排"变成写/编译/git 类动作的**前置条件**。

## 2. 门禁作用对象与时机

- **作用对象**：对已接入 pax-family 的项目（判定见 §3），Agent 对项目根的写操作、编译、构建、`git` 提交。
- **时机**：每次工具调用前的拦截点。Proma 已有 `beforeToolCall`（projectInstructionScope）与
  `canUseTool` 回调，可作为挂载点；两者任一可达即可。
- **放行的证据**：会话/项目存在「已达成本轮编排」的记录——例如：
  - 存在 `.pax/plan/pax-snapshot.yaml`，且其为**本轮任务**生成（含意图、风险、diagnose_required、route）；
  - 或 Agent 已在当前会话调用过 `pax-orchestrate` 且未中途被用户打断。

## 3. 触发判定（哪些项目启用）

仅当同时满足以下条件才启用硬门禁，避免影响未接入家族的项目：

| 条件 | 判定 |
|---|---|
| 项目已接入 pax-family | `projectRoot` 下存在 `.pax/project-profile.json`，或存在含 `pax-family 强制规则` 的 `AGENTS.md` |
| 任务属家族意图 | 通过 pax-orchestrate 的分类（diagnose_fix / feature_dev / refactor / data_ops / tool_build）判断；纯 doc_consult 不强制 |
| 非只读动作 | 目标是写文件 / 编译 / 构建 / `git` 等会产生变更的动作 |

## 4. 拦截行为

命中 §2+§3 且未达成编排时，拦截该工具调用并返回如下语义（可由 canUseTool/beforeToolCall 呈现）：

```
该项目已接入 pax-family。当前任务尚未经过 L0 编排入口（pax-orchestrate），
按项目 AGENTS.md 约定，禁止在达成编排前直接执行写/编译/git 操作。
请先调用 pax-orchestrate 产出任务快照（intent、risk、diagnose_required、route），
再按快照路由调度下游阶段。若你确需跳过编排，请选择"跳过编排继续"。
```

## 5. 放行条件（不拦截）

任一项成立即放行：

1. **已达成编排**：存在本轮 `pax-snapshot.yaml`，或本会话已调用 `pax-orchestrate`。
2. **用户显式跳过**（跳过通道）：用户明确选择"跳过编排"。这是刻意保留的人为出口，避免过度阻塞
   一次性解释类或用户已自行判断的场景。跳过动作应留痕（记录到会话，便于审计）。
3. **未接入家族 / 非家族意图 / 只读动作**：不启用（§3 未全部命中）。
4. **门禁自身故障**：无法判断项目是否接入/是否达成编排时，按放行处理并记录告警，避免因误判阻断正常开发。

## 6. 边界与安全

- 门禁只做"前置条件"拦截，不改变工具本身能力；用户可通过跳过通道继续。
- 跳过通道 MUST 是用户主动选择，不由模型自行决定，否则又退回软约束。
- 对 README/文档/纯咨询类（doc_consult）不强加编排，避免无意义摩擦。
- 门禁判定失败默认放行（fail-open），并告警；避免因机制问题锁死项目。

## 7. 验收标准

1. **拦截达成**：对已接入家族项目，Agent 未编排即写文件/编译/git 时，工具被拦截并给出 §4 提示。
2. **放行正常**：达成编排后同类动作放行；未接入项目不受影响。
3. **跳过可用**：用户显式选择跳过后可继续，且留痕。
4. **不误伤**：doc_consult / 未接入 / 只读动作不触发。
5. **fail-open**：门禁功能异常时降级为放行 + 告警，不中断开发。

## 8. 参考证据

- `agent-runtime.cjs`：`resolveProjectInstructions`、`projectInstructionScope.beforeToolCall`、
  `appendPendingInstructions`、`combinePromaInstructionFiles`。
- `main.cjs`：`getProjectFilesPath(workspaceSlug)`、`readWorkspaceAgentsMd(workspaceSlug)`、
  `canUseTool` 回调、`wrapToolWithPermission`。
- 会话 7129e309 system prompt：`<project_instructions path="D:\workspaces\cmp-preview\AGENTS.md">` 已含
  但未被执行约束。

## 9. 现状边界

- 本契约由 pax-family（pax-skills 仓库）定义；**不**包含在 pax-forge 内实现（pax-forge 是纯 CLI，
  无运行时拦截能力）。
- 落地需 Proma 运行时接入本契约；在此之前，软绑定强化（AGENTS.md.tmpl + orchestrate skill 措辞）
  作为缓解手段，见 `evals/datasets/instruction-compliance/ic_v1.0.json` 与 `evals/run_ic_eval.py` 的评估。
