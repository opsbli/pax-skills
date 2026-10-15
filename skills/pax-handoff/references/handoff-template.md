# Handoff 模板（v1.0）

供 `pax-handoff mode=emit` 生成 handoff.md 时使用。**严格按以下 10 段顺序**，顺序不可变。

> 该文件是 SKILL.md 引用的模板资源，可自由引用其他 skill 名（不在 contracts.py 扫描范围内）。

---

```markdown
# Handoff: <project> · <scope>

## meta
- **from_session**: `<session_id>`
- **from_session_title**: <title>
- **from_session_last_active**: <ISO8601>
- **to_workspace**: `<workspace_slug>`
- **project_root**: <absolute_path>
- **created_at**: <ISO8601>
- **purpose**: <一句话>
- **handoff_path**: `~/.proma/agent-workspaces/<workspace>/_handoff/<name>.md`

## goal
<一句话目标；来自快照 goal.statement>

## current_state
<当前进度，含证据：commits（sha + subject）、验证结果（typecheck/tests/manual）、
 待确认状态。含具体数字与 commit 链，方便新会话快速定位。>

## snapshot_path（继承策略）
`<旧 snapshot 绝对路径>`

<快照含 X、Y、Z——不在此重复，直接读文件。
 继承策略：新会话读旧 snapshot 后，将 meta/goal/consensus 段作为起点继承，
 只新增 orchestration.annotations.resume_from: <from_session>；
 其余字段由新会话的编排入口重跑覆盖。>

## 已用户确认的关键裁决
<列表；来自快照 consensus.user_confirmed_decisions；
 新会话直接消费，不再询问>

## artifacts（只引用，不复制）
| 类型 | 路径 |
|---|---|
| <type1> | `<path1>` |
| <type2> | `<path2>` |

## deferred / open items（按优先级）
<列表；**只写"要改什么"，不写"改哪个文件第几行"**——位置让新会话现场 grep；
 这是 M1→M2 实测教训（模板验证时 handoff 里写死的行号与源码实际不符，
 新会话读源码后发现并跳过，不影响结果但暴露了行号漂移问题）>

## next_focus（建议顺序）
<有序列表；每条一个原子动作；含"读 X → 做 Y → commit Z"的具体节奏>

## suggested_skills
<新会话开头的下游 skill 链；起手必为编排入口（`/skill:pax-orchestrate`）；
 明确 resume_from 应写入的位置；
 若涉及新接口契约，追加设计阶段（pax-design）；
 若可能告警/回归，追加监控/回滚阶段（pax-monitor / pax-rollback）>

## 新会话续接提示词（直接复制粘贴即可）

/skill:pax-orchestrate 续接 <project> <scope>。

前情提要：
- project_root: <path>
- handoff: <handoff_path>
- snapshot: <snapshot_path>

本轮任务：
- 先读 handoff 和 snapshot 确认状态；snapshot 的 meta/goal/consensus 继承，其他字段由本次编排重跑
- 走完整编排流程（意图=<intent> 续接，risk 需重评；annotations.resume_from = <from_session>）
- 优先处理 <first_action>，单独 commit
- 完成后按规划段的 deferred 清单继续，每子任务独立 commit

## redacted
<脱敏声明；若含敏感信息，说明已脱敏；否则声明"无敏感字段">
```

---

## 使用约定

- **落点**：`~/.proma/agent-workspaces/<workspace>/_handoff/<name>.md`（工作区共享目录，不绑 session ID，不进项目仓）
- **命名**：`<milestone>-to-<milestone>` 或 `<task>-checkpoint-<date>`
- **引用不复制**：snapshot/plan/PRD/commit 等已有 artifact 只写路径，不复制内容
- **行号漂移防护**：`deferred` 只写"要改什么"，不写"改哪个文件第几行"
- **脱敏**：emit 前扫描 API key / 密码 / PII / 支付凭证，命中则删除并在 `redacted` 段声明
