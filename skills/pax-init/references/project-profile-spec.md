# project-profile 规格

> 本文件是 `.pax/project-profile.json` 的**字段规格单一事实源**，同时定义 `AGENTS.md` 内嵌摘要的对应关系。
> `templates/project-profile.json.tmpl` 是结构模板；字段语义与消费规则以本文件为准。

## 1. 定位

`project-profile.json` 是**项目元数据的机器可读快照**，由 `pax-init` 生成，落在目标项目根目录的 `.pax/` 下。
它回答的是「这个项目是什么、用什么技术栈、遵循什么规范、怎么构建验证」，让后续阶段不必每次重新探测项目事实。

它**不是** pax 任务快照：

| 对比项 | `pax-snapshot.yaml` | `.pax/project-profile.json` |
|---|---|---|
| 作用域 | 单次任务的生命周期状态 | 单个项目的长期元数据 |
| 生命周期 | 任务结束即归档 | 项目规范变更时才重新生成 |
| 生产方 | L0 编排入口 | `pax-init` |
| 消费方 | L1 各阶段 | L1 规划 / 执行 / 评审层 |
| 契约 | `schemas/snapshot.schema.json` | 本文件 |

## 2. 字段规格

| 字段 | 类型 | 必填 | 说明 | 主要消费方 |
|---|---|---|---|---|
| `profile_version` | string | ✅ | 本规格的版本，当前 `"1.0"` | 全部 |
| `generated_by` | string | ✅ | 形如 `pax-init@0.2.0` | 审计 |
| `generated_at` | string | ✅ | ISO 8601 时间戳 | 审计 |
| `family` | object | ✅ | `{name: "pax", version: "<家族版本>"}`，家族版本取自 `pax-ops/versions.json` | 全部 |
| `mode` | string | ✅ | `single_project` / `multi_project` | 全部 |
| `project_name` | string | ✅ | 项目名，与 `AGENTS.md` 标题一致 | 全部 |
| `project_description` | string | ⬜ | 一句话说明 | 全部 |
| `repo_path` | string | ✅ | 后端 / 主仓库根路径 | L1 执行层 |
| `tech_stack` | array | ✅ | 每项 `{target, evidence_file, extracted}`；未检测到的项 `evidence_file: null` 且 `extracted: "未检测到"` | L1 规划 / 执行层 |
| `directory_structure` | object | ⬜ | `{root_files, key_directories, entry_points}` | L1 规划层 |
| `coding_standards` | object | ⬜ | `{language, framework, naming_convention, layering_pattern, linter, formatter}` | L1 执行层 |
| `build_commands` | object | ✅ | `{build, test, lint}`；未识别的命令留空字符串，不得编造 | L1 执行 / 评审层 |
| `standards_doc` | object | ✅ | 项目自有规范文档指针，见 §3 | L1 执行 / 评审层 |
| `db_conventions` | object | ⬜ | 代码生成器字段规范，见 §4 | L1 规划 / 执行层 |
| `frontend` | object | ⬜ | `{path, framework, ui_library, css_framework, state_management, package_manager, package_manager_note}` | L1 执行层 |
| `artifacts_dir` | string | ✅ | 产物目录名，固定 `".pax"` | 全部 |
| `risk_sensitive` | boolean | ⬜ | 项目涉及生产数据 / 支付 / 认证时标注，提示手工复核 | L1 评审层 |

## 3. `standards_doc` 唯一事实源指针（防双源漂移）

项目已有规范文档时，profile **只写结构化摘要 + 指针**，NEVER 全文复制。

```json
{
  "path": "docs/agents/project-standards.md",
  "status": "present",
  "consumption_rule": "L1 规划 / 执行 / 评审层 MUST 完整阅读该文件后逐条对照执行；profile 仅是结构化摘要，与该文件冲突时以该文件为准",
  "sections": ["coding_standards", "db_conventions", "naming"]
}
```

规则：

1. 未检测到项目级规范文档时，`path` 为空字符串、`status` 为 `"absent"`，并记录 `skip_reason`。
2. `sections` 只登记**已确认存在**的章节名，NEVER 臆造章节。
3. 摘要与原文冲突时**以原文为准**，这是硬规则，不可由下游自行改写。
4. 已知教训：首次生成若漏掉指针，profile 会与项目已确认规范脱节——下游按过期口径执行且无人察觉。指针字段 MUST 每次生成都显式落盘（哪怕是 `absent`）。

## 4. `db_conventions`

检测到代码生成器时，字段规范 MUST 从**项目基类与建表模板实际提取**，NEVER 套用外部默认字段名：

```json
{
  "source": "ruoyi-generator",
  "code_generator": "ruoyi-generator",
  "tenant_fields": [{"name": "tenant_id", "type": "VARCHAR(20)", "note": "租户编号"}],
  "audit_fields": [
    {"name": "create_dept", "type": "BIGINT", "note": "创建部门"},
    {"name": "create_by", "type": "BIGINT", "note": "创建者"},
    {"name": "create_time", "type": "DATETIME", "note": "创建时间"},
    {"name": "update_by", "type": "BIGINT", "note": "更新者"},
    {"name": "update_time", "type": "DATETIME", "note": "更新时间"}
  ],
  "logical_delete": {"name": "del_flag", "type": "CHAR(1)", "values": {"0": "存在", "1": "删除"}}
}
```

未检测到代码生成器时，使用通用规范（`id` / `created_at` / `updated_at` / 可选 `deleted_at`），
并把 `source` 设为 `"generic"`、记录 `skip_reason`。

## 5. `AGENTS.md` 内嵌摘要的一致性

`AGENTS.md` 中的 `project-profile 摘要` 区块 MUST 与 `.pax/project-profile.json` 同源：

| profile 字段 | `AGENTS.md` 摘要中的呈现 |
|---|---|
| `project_name` / `project_description` | 项目概述表 |
| `tech_stack` | 技术栈章节（含证据文件） |
| `coding_standards` | 编码规范章节 |
| `build_commands` | 构建与验证命令章节 |
| `standards_doc.path` + `consumption_rule` | 规范文档指针章节（含「以原文为准」提示） |

一致性校验：生成后对比两处的 `project_name` / `tech_stack` 目标集合 / `build_commands` 三项，任一处不同即视为生成失败，必须重生成。

## 6. 版本演进

- `profile_version` 变更（新增 / 删除必填字段）属于**下游契约变更**：MUST 先更新本文件与 `templates/project-profile.json.tmpl`，再评估家族兼容矩阵是否触发 major bump。
- 新增**可选**字段不触发 major bump，但 MUST 同步本文件、模板与 `AGENTS.md` 摘要呈现规则。
