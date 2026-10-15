---
name: pax-handoff
description: >
    Use when: 长会话上下文交接，跨会话续接任务。当当前会话上下文紧张、
    或用户明确说"换会话继续"/"新开会话续接"时，通过 `/skill:pax-handoff`
    显式调用；也可被 `pax-plan` 中标注 `execution_strategy: manual_handoff`
    的步骤引用（用户手动确认场景）。**用户直接调用型**，不由 pax-orchestrate
    自动挂载。产出 `<workspace>/_handoff/<name>.md` 供新会话 resume 加载。
version: 1.0.0
family: pax
layer: L4
optional: true
requires_snapshot: true
disable-model-invocation: true
upstream: "mattpocock/skills#skills/productivity/handoff"
---

# pax-handoff


## Overview

跨会话交接 Skill。把当前会话的"值得传下去"的信息压缩成一份 handoff.md，
供新会话读取后按家族契约续接任务。**引用不复制**——snapshot/plan/PRD/commit
等已有 artifact 只写路径，不重复其内容。**双向**：emit 方向由用户显式调用，
resume 方向供新会话按约定位置加载。

## When to Use

- 当前会话上下文过长（用户显式说"要换会话继续"）
- 用户明确 `/skill:pax-handoff`
- 规划阶段中某步骤标注 `execution_strategy: manual_handoff`，用户手动确认后
- 一次长任务的**自然 checkpoint**（例：一个 milestone 完成后）

**不适用**：

- 同一会话内的短期上下文整理（直接用 prompt 收敛即可）
- 任务尚未产出实质内容（无 handoff 价值）
- 会话仅几个 turn（继续用就好，不需要交接）

## Common Pitfalls

- **deferred 写具体行号**：M1 期间的代码在跑，交接时快照的行号可能已经漂移；
  `deferred` 只写"要改什么"（语义），不写"改哪个文件的第几行"（位置）。
  具体位置让新会话现场 grep。这是从 pax-md M1→M2 实测得到的教训。
- **复制 snapshot 内容**：handoff.md 是自然语言摘要 + 指针，不是 snapshot 副本。
  快照/计划/PRD/ADR 只写路径引用。
- **写用户偏好之外的假设**：不预测"下次要写文档"这种未经用户确认的意图。
- **写进项目仓**：handoff.md 是任务级时效性产物，落工作区 `_handoff/`，
  不进 git（不污染正式产物）。
- **忘记脱敏**：API key、密码、PII、支付凭证等必须在 emit 前扫描过滤。
- **不写续接提示词**：缺少"新会话续接提示词"块，用户还得自己拼 prompt。

## Verification Checklist

- [ ] handoff.md 落在 `<workspace>/_handoff/<name>.md`（未污染项目仓）
- [ ] 10 个必备字段齐全：`meta / goal / current_state / snapshot_path /
      key_decisions / artifacts / deferred / next_focus / suggested_skills / redacted`
- [ ] 每个引用（snapshot/plan/PRD/commit）都是**路径**，未复制内容
- [ ] 脱敏已完成（无 API key/密码/PII/支付凭证）
- [ ] `suggested_skills` 段明确下游 skill 链（起手必为家族编排入口；仅作为建议内容嵌入 handoff.md，本 skill 不实际调用）
- [ ] 含"新会话续接提示词"块，可直接复制粘贴
- [ ] `deferred` 只写"要改什么"，未写具体行号
- [ ] `resume_from` 字段已写入（若为续接场景）
- [ ] `disable-model-invocation: true` 未被移除
- [ ] 未越权改动业务快照的 `consensus/diagnosis/plan/execution/review` 字段

## Execution Contract

- **前置门禁**：可被任意 L0/L1/L2/L4 调用（横切）；仅用户显式调用（`disable-model-invocation: true`）
- **未通过门禁**：返回 `blocked`（未拿到用户显式意图时不启动）
- **版本检查**：`pax-ops/versions.json`
- **触发方式**：`disable-model-invocation: true`——**只允许用户显式 `/skill:pax-handoff` 调用**，
  模型不得自作主张触发。这是本 skill 对齐 mattpocock/handoff 的核心约束。
- **模式**：`mode=emit`（生成 handoff.md，默认）| `mode=resume`（新会话加载并续接）
- **argument-hint**：`"下一会话打算聚焦什么？"`（可选，改变文档侧重）
- **落点契约**：`~/.proma/agent-workspaces/<workspace>/_handoff/<name>.md`
- **引用不复制**：handoff.md 是自然语言摘要 + 指针，重复已存在 artifact 内容视为 bug
- **脱敏铁律**：emit 前必须扫描过滤 API key / 密码 / PII / 支付凭证
- **deferred 行号漂移防护**：`deferred` 只写"要改什么"，不写"改哪个文件第几行"；
  位置让新会话现场 grep
- **旧快照保留**：不复制、不移动旧 snapshot；新会话通过
  `orchestration.annotations.resume_from: <old_session_id>` 关联
- **不改动业务快照字段**：禁止修改旧 snapshot 的 `consensus/diagnosis/plan/execution/review`
- **快照记录（可选）**：如需在快照中留痕，由学习阶段自行决定字段与位置；
  本 skill **不承诺**任何具体 snapshot 字段，也 **不修改** 业务快照的
  `consensus/diagnosis/plan/execution/review` 段
- **skip_reason**：可选 skill，本 skill 无“强制触发”场景。当用户未显式调用、或无需 checkpoint 时，
  不启动即为本 skill 的“正常跳过”，无需在快照中写入 skip_reason

## 职责边界

- **做什么**：
  - `mode=emit`：把当前会话上下文压缩为 handoff.md，落到 `<workspace>/_handoff/`
  - `mode=resume`：新会话加载 handoff.md 与旧 snapshot，产出结构化续接摘要交给下游编排入口
- **不做什么**：
  - 不复制 snapshot/plan/PRD/ADR/commit 内容（只引路径）
  - 不修改旧 snapshot 的业务字段
  - 不改变 pax 家族主路由（`clarify/plan/execute/review` 顺序不变）
  - 不承载"任务级状态"（那是 snapshot 的职责）
  - 不认领路由落点（横切，用户显式调用）
  - 不做代码分析或方案裁决（那是分析/咨询阶段的职责）
  - 不主动调用其他 skill（本 skill 仅为“交付一份 handoff.md + 续接摘要”，下游链路仅写入模板作为建议）

## 输入

- **必需**：
  - `mode`: `"emit"` 或 `"resume"`
  - `workspace_slug`: 目标工作区名（默认当前工作区）
- **可选**：
  - `name`: handoff.md 文件名（默认按 `<milestone_or_scope>.md` 命名）
  - `next_focus`: 用户说明"下一会话打算聚焦什么"（改变文档侧重，可省略）
  - `resume_from`: `mode=resume` 时旧会话 ID（可从 handoff.md 的 `meta.from_session` 读）
  - `snapshot_path`: `mode=resume` 时旧 snapshot 路径（可从 handoff.md 的 `snapshot_path` 读）

## 工作流

### H1 触发确认（Trigger Confirmation）

确认用户显式调用，判断 mode：

```python
def confirm_trigger(user_input):
    """
    确认用户显式调用本 skill。
    - 若 user_input 不含 /skill:pax-handoff 前缀，返回 blocked
    - 从参数解析 mode（默认 emit）与 name（默认按 scope 生成）
    """
    if not user_input.startswith("/skill:pax-handoff"):
        return {"status": "blocked", "reason": "handoff 仅用户显式调用"}
    mode = user_input.get("mode", "emit")
    name = user_input.get("name") or derive_name_from_snapshot()
    return {"status": "ok", "mode": mode, "name": name}
```

### H2 Emit：抽取上下文（Context Extraction）

从**当前会话**读取以下事实（不重新做分析，只做摘要）：

| 事实 | 来源 | 摘要形式 |
|---|---|---|
| 会话 ID / 标题 / 最后活跃时间 | 当前会话元数据 | `meta.from_session*` |
| 目标 / 已完成 / 未完成 | `pax-snapshot.yaml`（若存在） | `goal` / `current_state` / `deferred` |
| 已确认决策 | 快照 `consensus.user_confirmed_decisions` | `key_decisions` |
| 相关 artifact | 快照引用 + 当前工作区文件 | `artifacts` |
| 下一步 | 快照 subtasks + 上一轮助手回复 | `next_focus` |
| 建议下游 skill | 家族契约 + 意图 | `suggested_skills` |

### H3 Emit：字段生成规则（Field Generation Rules）

handoff.md 严格按 10 段顺序生成：**meta / goal / current_state / snapshot_path / key_decisions / artifacts / deferred / next_focus / suggested_skills / redacted**，顺序不可变。

**完整模板**（含每段字段说明、行号漂移防护、新会话续接提示词块）见：

```
references/handoff-template.md
```

本 SKILL.md 仅描述 emit/resume 的执行规则；模板作为静态资产独立存放（便于单独演化、版本化、预览）。

**引用不复制**：模板中的 `snapshot_path / artifacts` 仅写入路径；snapshot/plan/PRD/commit 内容不重复到 handoff.md。

**建议下游链路**：模板里的 `suggested_skills` 段仅作为 handoff.md 的文本内容（供新会话复制），本 skill 自身不执行、不发起下游调用。

### H4 Emit：落点选择（Placement）

```python
def choose_output_path(workspace_slug, name):
    """
    契约固定：~/.proma/agent-workspaces/<workspace_slug>/_handoff/<name>.md
    - 不绑 session ID（换 session 也能找到）
    - 不进项目仓（不污染 git）
    - 目录不存在则创建
    """
    base = f"~/.proma/agent-workspaces/{workspace_slug}/_handoff"
    ensure_dir(base)
    return f"{base}/{name}.md"
```

**落点契约**（写入 CHANGELOG，用户可查）：

| 落点 | 用途 |
|---|---|
| `~/.proma/agent-workspaces/<workspace>/_handoff/<name>.md` | 工作区共享，跨 session 可读，不进 git |
| ❌ `<project_root>/.context/handoff/` | 会跟项目 git 混，本 skill 不采用 |
| ❌ `~/.proma/agent-workspaces/<workspace>/<session_id>/handoff.md` | 绑死 session ID，不推荐 |
| ❌ 系统 temp 目录 | mattpocock 方案，不适合 pax 家族（无法通过约定位置发现） |

### H5 Emit：脱敏与引用不复制（Redaction & No-Replication）

emit 前必须执行两道扫描：

```python
def scan_for_sensitive(text):
    """
    检测并标记敏感字段：
    - API key / token（sk-、ghp_、xoxb-、AKIA 等前缀）
    - 密码（明文或 base64）
    - PII（身份证号、手机号、支付凭证、银行卡号）
    - 私钥（-----BEGIN RSA PRIVATE KEY----- 等）
    命中后：
    - 从 handoff.md 中删除
    - 在 redacted 段声明"含敏感信息，已脱敏，字段名 X"
    - 绝不写入 handoff.md 正文
    """
    patterns = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"ghp_[a-zA-Z0-9]{20,}",
        r"xox[baprs]-[a-zA-Z0-9-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        # ... 更多 PII 模式
    ]
    return [p for p in patterns if re.search(p, text)]

def verify_no_replication(handoff_content, referenced_files):
    """
    引用不复制验证：
    - 对每个 referenced_files 中的文件，检查 handoff_content 是否含其原文段落（≥50 字符）
    - 若命中，视为 bug，要求改为路径引用
    """
    for path in referenced_files:
        original = read_file(path)
        for chunk in chunk_by_50_chars(original):
            if chunk in handoff_content:
                return False, path
    return True, None
```

### H6 Resume：加载并续接（Resume）

新会话开头调用 `mode=resume`，按以下步骤加载：

```python
def resume(workspace_slug, handoff_path=None, snapshot_path=None):
    """
    1. 若未指定 handoff_path，扫 <workspace>/_handoff/ 找最新的 .md
    2. 读 handoff.md，抽 meta.from_session + snapshot_path
    3. 读旧 snapshot（不修改）
    4. 产出"续接摘要"，交给下游编排入口消费
    """
    handoff = load(handoff_path or scan_latest_handoff(workspace_slug))
    snapshot = load(handoff.snapshot_path)

    return {
        "meta": snapshot.meta,
        "goal": snapshot.goal,
        "consensus": snapshot.consensus,
        "resume_from": handoff.meta.from_session,
        "deferred": handoff.deferred,
        "next_focus": handoff.next_focus,
        "artifacts": handoff.artifacts,
        "instruction": "走完整编排流程，重跑 intent/risk/route/annotations；annotations.resume_from 已注入"
    }
```

### H7 快照留痕（Snapshot Trace）

**本 skill 不声明具体快照字段**。理由：

- `snapshot.learning` 在 `schemas/snapshot.schema.json` 中为 `additionalProperties: false`，仅允许 `experiences / knowledge_graph / recommendations` 三个字段，直接新增 `handoff_emit / handoff_resume` 会破坏 schema
- 家族内其他可选 skill 也不各自新增顶层学习字段——学习阶段的字段归属由学习阶段统一决定

**如果需要追踪 handoff 使用频率与质量**，推荐路径：

1. 将本轮 emit/resume 事件作为一条经验条目写入学习阶段已有的经验数组（不新增字段）
2. 或在 `recommendations` 里追加一条“关于 handoff 使用模式”的建议
3. 或依靠会话日志（不在快照里）做事后分析

本 skill 在文档中不硬编码任何 `snapshot.<section>.<field>` 路径，避免引入家族内未声明的字段。

## 输出契约

- **`mode=emit`**：
  - `~/.proma/agent-workspaces/<workspace>/_handoff/<name>.md`（10 字段齐全，模板见 `references/handoff-template.md`）
  - 一段"新会话续接提示词"文本块（在 handoff.md 内嵌，供用户复制）
  - 可选：若家族其他阶段需要在快照中记录，交学习阶段决定字段与位置（本 skill 不承诺具体字段）
- **`mode=resume`**：
  - 一份结构化"续接摘要"，含继承的 `meta / goal / consensus` + 注入的 `resume_from`
  - 同上，可选地由学习阶段补充留痕
- **不新增 `snapshot.schema.json` 字段**（学习段已为 `additionalProperties: false`）

## 失败模式

- **未显式调用** → 返回 `blocked`，不启动（`disable-model-invocation` 生效）
- **无当前快照**（emit 时）→ 允许继续，但 `current_state` 段需从会话上下文现场抽取，`snapshot_path` 段留空并标注"无快照"
- **无 handoff.md 可加载**（resume 时）→ 返回 `blocked`，列出 `_handoff/` 目录当前内容
- **敏感信息命中** → 从 handoff.md 移除，在 `redacted` 段声明，正文不出现
- **引用不复制验证失败** → 停止 emit，报错要求改为路径引用
- **落点目录不存在** → 自动创建（`_handoff/`），不询问用户
- **旧 snapshot 不存在或损坏**（resume 时）→ 只加载 handoff.md 部分，`resume_from` 仍记录，提示用户"旧快照不可读，请人工确认"
- **handoff.md 与 snapshot 冲突**（例：`deferred` 与快照状态不一致）→ 以 snapshot 为准，handoff.md 记录"以快照为准"标注

## 何时升级

- 涉及敏感字段脱敏判断存疑 → 保守脱敏，写入 `redacted` 段留痕，必要时请用户确认
- 家族契约与 handoff 模板冲突 → 家族契约优先，本 skill 更新对齐
- 用户在续接提示词里给出的目标与 handoff.md 的 `next_focus` 冲突 → 以用户输入为准，`resume` 时更新 `next_focus`
- 落点目录跨工作区访问受限 → 请求用户手工指定落点
- 本 skill 使用频率低（学习阶段发现）→ 建议合并到规划阶段的 `manual_handoff` 语义，或移除
