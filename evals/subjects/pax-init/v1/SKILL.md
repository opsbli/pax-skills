---
name: pax-init
description: >
    Use when: 把一个新项目或既有项目接入 pax-family 开发流程。L4 层内部工具，由用户直接调用，不认领编排路由落点：扫描项目目录检测技术栈（Java/Maven、RuoYi、TS/Vite/Vue、Go、Python 等），发现项目既有规范文档，生成 AGENTS.md（AI 协作编码规范）与 .pax/project-profile.json（机器可读项目元数据），并创建 .pax/ 产物目录。检测到代码生成器时严格提取其租户字段 / 审计字段 / 逻辑删除字段规范。已有 AGENTS.md 时必须先请用户确认覆盖 / 合并 / 跳过。
version: 0.2.0
family: pax
layer: L4
optional: true
requires_snapshot: false
---

# pax-init


## Overview

项目接入 Skill。把一个目标项目（新项目或既有项目）接进 pax-family：扫描技术栈 → 发现项目自有规范文档 → 生成 `AGENTS.md`（人可读的 AI 协作编码规范）与 `.pax/project-profile.json`（机器可读的项目元数据）→ 创建 `.pax/` 产物目录。之后 L1 规划 / 执行 / 评审层可以直接消费 project-profile，不必每次重新探测项目事实。

## When to Use

- 用户要求「初始化这个项目」「把某个项目接入 pax-family」「帮我生成这个项目的 AGENTS.md」。
- 目标项目缺少 `AGENTS.md` 或 `.pax/project-profile.json`，下游 L1 阶段提示「建议先做项目接入」。
- 项目技术栈、构建命令、数据库字段规范发生变化，需要重新生成 profile。

本 Skill 是**直接调用型内部工具**：不认领编排路由落点，不需要跨 Skill 快照，`requires_snapshot: false`。用户给出项目路径即视为激活本工作流。

## Common Pitfalls

- 未确认项目路径就开始扫描，甚至为不存在的路径创建目录。
- 技术栈靠猜而不看特征文件，检测不到却写成「大概是用 X」。
- 直接覆盖目标项目已有的 `AGENTS.md`，抹掉用户手写规则。
- 把项目自有规范文档全文复制进 profile，造成双源漂移：文档改了、profile 没改，下游按过期口径执行。
- 只产出机器可读 JSON，不同步 `AGENTS.md` 里的摘要，两者数据不一致。
- 重复运行生成重复目录或重复段落，破坏幂等。

## Verification Checklist

- [ ] 已声明模式（单项目 / 多项目）、目标路径、扫描结果、`AGENTS.md` 处置、`.pax/` 状态
- [ ] 每一项技术栈结论都能指向具体特征文件（存在即命中，不存在标「未检测到」）
- [ ] 已有 `AGENTS.md` 时已取得用户明确三选一（覆盖 / 合并 / 跳过），未静默覆盖
- [ ] 项目自有规范文档只做结构化摘要 + 指针（path / status / consumption_rule / sections）
- [ ] `project-profile.json` 与 `AGENTS.md` 内的 profile 摘要字段一致
- [ ] 重复运行结果相同（幂等：不重复建目录、不重复插段落）

## Execution Contract

> 本节定义「被激活后必须做什么」，优先级高于 Agent 的通用默认行为。用户给出项目路径即视为激活，MUST NOT 仅把本文件当参考文档。

0. **版本门（第零步）**：执行入口启动后、核心步骤前，MUST 先读取 `pax-ops/versions.json`，确认家族版本与本 Skill 版本一致（本 Skill 当前 `0.2.0`）。版本门自身故障时放行并标注口径，NEVER 因版本门故障阻断本 Skill 启动。
1. **模式强制**：激活后 MUST 先判定**单项目模式**还是**多项目模式**（前后端分离），再读取路径。NEVER 在未确认项目路径的情况下开始扫描。
2. **扫描诚实铁律**：技术栈结论 MUST 基于特征文件的**实际存在**，NEVER 猜测。检测不到标「未检测到」并请用户手动指定，NEVER 编造。
3. **AGENTS.md 保护铁律**：目标项目已有 `AGENTS.md` 时，MUST 展示现有内容摘要并请用户在「覆盖重新生成 / 保留合并 / 跳过」中明确选择，NEVER 静默覆盖。
4. **唯一事实源指针铁律**：目标项目已有规范文档（如 `docs/agents/project-standards.md`、`CONTEXT.md`、`docs/adr/`）时，profile 只写**结构化摘要 + 指针**，NEVER 全文复制；摘要与原文冲突时以原文为准。
5. **双格式一致铁律**：MUST 同时产出 `.pax/project-profile.json`（机器可读）与 `AGENTS.md` 内嵌的 profile 摘要（人可读），两者字段 MUST 一致。
6. **代码生成器规范铁律**：检测到代码生成器模块（如 RuoYi generator）时，MUST 从项目基类/建表模板提取实际的**租户字段**与**审计字段**与**逻辑删除字段**，NEVER 套用外部默认字段名。
7. **幂等性**：重复运行 MUST 产生相同结果，NEVER 重复创建已存在的目录或重复插入已存在的段落。
8. **自检声明**：作答前 MUST 声明「本次模式=＜单项目/多项目＞，目标路径=＜路径＞，已扫描，技术栈=＜检测结果＞，AGENTS.md=＜新建/覆盖/合并/跳过＞，.pax=＜已创建/已存在＞」。

- 前置门禁：① 目标项目路径已确认且**实际存在**（用户明确提供或已在上下文中确认）；② 已判定单项目 / 多项目模式；③ `pax-ops/versions.json` 可读。
- 未通过门禁：返回 `blocked`，列出缺失项并请用户补齐；存在不满足项时**禁止**开始扫描。NEVER 为不存在的路径创建目录。
- 降级路径：Python 运行时可用的宿主可用 `scripts/scan_project.py` 取得确定性扫描证据；不可用时按 `references/tech-stack-detection.md` 逐条人工核对，结论口径不变。
- 跳过留痕：任何跳过都 MUST 记录 `skip_reason`，例如`AGENTS.md 跳过（用户选择保留）`、`代码生成器规范降级为通用规范（未检测到代码生成器）`、`package_manager 未采信 lock 文件（用户确认为 pnpm）`。
- 版本检查：`pax-ops/versions.json`（家族版本与本 Skill 版本的唯一来源）。
- 禁止：静默覆盖已有 `AGENTS.md`；未确认路径即扫描；猜测或编造技术栈；全文复制项目自有规范文档；为不存在的路径创建目录。

## 职责边界

- 做什么：扫描项目 → 检测技术栈 → 提取代码生成器规范 → 发现项目规范文档指针 → 生成 `AGENTS.md` → 生成 `.pax/project-profile.json` → 创建 `.pax/` 产物目录。
- 不做什么：不写业务代码、不做根因诊断、不生成执行计划、不评审代码、不生成或校验 pax-family 自身的 Skill、不安装 Skill、不管理家族版本。

相邻边界（按层与角色描述，避免与本 Skill 产生调用边）：

| 相邻能力 | 边界判据 |
|---|---|
| 元层生成工具 | 那条线生成与校验 **Skill 包**；本 Skill 初始化 **目标项目环境**，让项目能被家族流程消费 |
| L0 编排入口 | 编排入口消费 **任务快照** 做路由；本 Skill 产出 **项目元数据**，不进快照、不参与路由 |
| L1 规划层 | 规划层消费 project-profile 里的构建命令与验收字段；本 Skill 只生成该文件 |
| L1 执行层 | 执行层消费 project-profile 里的编码规范与数据库字段规范；本 Skill 只生成该文件 |
| L1 评审层 | 评审层按 project-profile 指向的规范文档逐条对照；本 Skill 只登记指针，不复制原文 |
| L4 文档沉淀层 | 文档沉淀层向项目写决策记录 / 案例；本 Skill 只写 `AGENTS.md` 与 project-profile，二者产物不重叠 |

## 输入

| 字段 | 必填 | 说明 |
|---|---|---|
| 项目路径 | ✅ | 单项目根目录，或多项目模式下前后端各自的根目录（含 `pom.xml` / `go.mod` / `package.json` 等特征文件） |
| 项目名称 | ✅ | 用于 `AGENTS.md` 标题与 profile 的 `project_name` |
| 前端项目路径 | ⬜ | 前后端分离时提供；不含后端时按单项目处理 |
| 项目描述 | ⬜ | 一句话说明，缺省时由扫描结果与目录结构推导 |
| 技术栈偏好 | ⬜ | 自动检测不准确的字段，用户显式指定后以用户为准 |
| 代码生成器规范 | ⬜ | 项目使用代码生成器时，指定规范来源模块 |
| AGENTS.md 处置 | ⬜ | 三选一：覆盖重新生成 / 保留合并 / 跳过（已存在时必填） |
| 家族版本 | ⬜ | 写入 profile 的 `family.version`，缺省取 `pax-ops/versions.json` |

## 工作流

> 执行顺序固定：第零步版本门 → W1 模式判定 → W2–W4 扫描 → W5–W7 生成 → W8 交付。

### W1 模式判定（Mode Detection）

```python
def detect_mode(input_paths):
    """判定单项目 / 多项目模式。"""
    if input_paths.has_frontend and input_paths.has_backend:
        return "multi_project"     # 前后端分离：分别扫描，共享一份 profile
    if input_paths.has_frontend or input_paths.has_backend:
        return "single_project"
    return "blocked"               # 路径缺失或不存在：先澄清，禁止扫描
```

判定结果 MUST 写入自检声明与 profile 的 `mode` 字段。多项目模式下，`frontend.path` 与 `repo_path` 分别记录，profile 只产出**一份**（以业务主仓库为主，前端信息进 `frontend` 区）。

### W2 项目扫描（Tech Stack Scan）

按 `references/tech-stack-detection.md` 的特征文件表逐项检测，每命中一项记录：检测目标、特征文件、提取内容。

```python
def scan_tech_stack(root):
    """按 references/tech-stack-detection.md 的规则表逐项检测。

    宿主可运行 Python 时，直接调用 scripts/scan_project.py 取确定性证据；
    否则按同一张表人工核对。检测不到 → '未检测到'，禁止猜测。
    """
    findings = []                      # 每条 = {target, evidence_file, extracted}
    for rule in DETECTION_RULES:       # 规则表：references/tech-stack-detection.md
        hit = root / rule.feature_file
        if exists(hit):
            findings.append({
                "target": rule.target,
                "evidence_file": str(hit),
                "extracted": extract(rule, hit),
            })
        else:
            findings.append({
                "target": rule.target,
                "evidence_file": None,
                "extracted": "未检测到",   # 诚实标注，不猜
            })
    return findings
```

包管理器检测 MUST 按优先级表（pnpm > yarn > npm > 仅 package.json 视为未检测到）执行，且检测结果 MUST 交用户确认后才写入 profile——lock 文件可能是历史遗留产物。

### W3 代码生成器规范提取（Code Generator Conventions）

检测到代码生成器模块时，从项目基类与建表模板提取字段规范，写入 profile 的 `db_conventions`：

| 提取项 | 来源 | 写入字段 |
|---|---|---|
| 租户字段 | 项目基类（如 `TenantEntity`）或建表模板 | `db_conventions.tenant_fields` |
| 审计字段 | 项目基类（如 `BaseEntity`） | `db_conventions.audit_fields` |
| 逻辑删除字段 | 项目 `@TableLogic` 注解或列定义 | `db_conventions.logical_delete` |
| 代码生成器标识 | 生成器模块路径 | `db_conventions.code_generator` |

未检测到代码生成器时，写入 `references/project-profile-spec.md` 定义的通用规范，并记录 `skip_reason`。

### W4 规范文档发现（Standards Doc Discovery）

```python
def discover_standards_docs(root):
    """发现项目自有规范文档，只登记指针，不复制原文。"""
    candidates = [
        ("docs/agents/project-standards.md", "project_standards"),
        ("CONTEXT.md", "domain_glossary"),
        ("docs/adr/", "architecture_decisions"),
    ]
    found = []
    for path, kind in candidates:
        if exists(root / path):
            found.append({
                "path": path,
                "status": "present",
                "kind": kind,
                "consumption_rule": "下游阶段 MUST 完整阅读该文件后逐条对照执行；"
                                    "profile 仅是结构化摘要，冲突时以该文件为准",
            })
    return found
```

命中即写入 profile 的 `standards_doc`（含 `path` / `status` / `consumption_rule` / `sections`）。未命中时 `standards_doc.path` 留空并标注「未检测到项目级规范文档」。NEVER 把原文复制进 profile。

### W5 AGENTS.md 生成或确认（AGENTS.md Generation）

| 目标项目现状 | 处置 |
|---|---|
| 无 `AGENTS.md` | 按 `templates/AGENTS.md.tmpl` 渲染，填充占位符后写入项目根 |
| 已有 `AGENTS.md` | 展示现有内容摘要 + 三选一：**覆盖重新生成 / 保留合并 / 跳过**；未获用户确认前 NEVER 写入 |
| 用户选择「保留合并」 | 只追加 `pax-family 强制规则` 与 `project-profile 摘要` 两个区块，保留用户手写内容 |
| 用户选择「跳过」 | 不写 `AGENTS.md`，记录 `skip_reason`，profile 照常生成 |

`AGENTS.md` 生成前 MUST 把技术栈扫描结果呈现给用户确认，未获确认 NEVER 继续。

### W6 project-profile 生成（Profile Generation）

按 `templates/project-profile.json.tmpl` 与 `references/project-profile-spec.md` 渲染 `.pax/project-profile.json`，并把同一份数据的**人可读摘要**嵌入 `AGENTS.md`。

```python
def build_profile(scan, generator, standards, meta):
    """机器可读 profile；与 AGENTS.md 摘要同源，字段必须一致。"""
    return {
        "profile_version": "1.0",
        "generated_by": f"pax-init@{meta.self_version}",
        "generated_at": iso8601_now(),
        "family": {"name": "pax", "version": meta.family_version},
        "mode": meta.mode,
        "project_name": meta.project_name,
        "project_description": meta.project_description,
        "repo_path": meta.repo_path,
        "tech_stack": scan.findings,
        "directory_structure": scan.structure,
        "coding_standards": scan.coding_standards,
        "build_commands": scan.build_commands,
        "standards_doc": standards,
        "db_conventions": generator,
        "frontend": scan.frontend,
        "artifacts_dir": ".pax",
    }
```

### W7 .pax/ 目录创建（Artifacts Directory）

```python
def ensure_artifacts_dir(root):
    """幂等创建 .pax/ 及子目录。已存在则跳过，不重复创建。"""
    base = root / ".pax"
    created = []
    for sub in (".", "plan", "execute", "review", "docs"):
        d = base / sub
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    return created
```

子目录与家族阶段一一对应：`plan`（规划）、`execute`（执行）、`review`（评审）、`docs`（文档沉淀）。产物命名沿用家族统一规则：`<问题类型>_<YYYYMMDD>_<HHMMSS>_<会话ID前8位>`。

### W8 交付确认（Delivery）

输出初始化摘要：模式、路径、技术栈结论、`AGENTS.md` 处置、`.pax/` 状态、产物清单，以及后续操作指引（下游阶段将消费 profile 的哪些字段）。

## 输出契约

| 产物 | 位置 | 消费方与说明 |
|---|---|---|
| `AGENTS.md` | `<项目根>/AGENTS.md` | 人可读的 AI 协作编码规范，含 pax-family 强制规则与 profile 摘要 |
| `.pax/project-profile.json` | `<项目根>/.pax/project-profile.json` | 机器可读项目元数据；字段规格见 `references/project-profile-spec.md` |
| `.pax/` | `<项目根>/.pax/` | 产物目录（`plan` / `execute` / `review` / `docs`） |

落盘规则：

- 全部产物落在**目标项目根目录**下，不落在 pax-family 仓库内。
- `project-profile.json` 与 `AGENTS.md` 内嵌摘要 MUST 同源、字段一致。
- project-profile 不是 pax 快照，不写入 `pax-snapshot.yaml`，不占用快照的 `additionalProperties` 约束。
- 本 Skill 的 `requires_snapshot: false`：由用户直接调用，输入是项目路径而非快照。

## 失败模式

| 条件 | 行为 |
|---|---|
| 项目路径不存在 | 返回 `blocked`，请用户澄清路径；记录 `skip_reason`，NEVER 创建目录 |
| 未判定单 / 多项目模式 | 返回 `blocked`，先澄清模式 |
| `AGENTS.md` 已存在且用户未选择处置 | 返回 `blocked`，展示现有摘要并等待三选一 |
| 技术栈完全无法检测 | 标注「未检测到」+ 请用户手动指定，`skip_reason` 记录；不阻断 profile 生成 |
| 代码生成器规范无法提取 | 降级为通用规范（`references/project-profile-spec.md`），记录 `skip_reason` |
| profile 渲染失败 | 不写半成品文件，返回 `fail` 并保留已扫描结果供重试 |
| `.pax/` 已存在 | 幂等跳过，不重复创建，不覆盖已有产物 |
| 版本门自身故障 | 放行并标注口径，不阻断启动 |

## 何时升级

| 触发条件 | 升级动作 |
|---|---|
| 用户拒绝三选一且要求保留手写规则但结构复杂 | 请求人工确认合并策略，NEVER 自行合并 |
| 多项目模式下前后端规范互相冲突 | 暂停生成，列出冲突项请用户裁决 |
| 检测到项目使用多套代码生成器规范 | 请求决策层盲审，确认以哪套为准 |
| project-profile 的字段规格需要变更（影响下游契约） | 走家族版本门禁：先更新 `references/project-profile-spec.md` 与模板，再按兼容矩阵评估是否 major bump |
| 目标项目属于高风险仓（生产数据 / 支付 / 认证） | 在 profile 中标注 `risk_sensitive: true` 并提示用户手工复核 |
