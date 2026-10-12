---
name: pax-gate
description: >
    Use when: 发布前需要做安全 / 合规 / 可访问性 / 许可证静态检查（SAST、密钥泄漏、依赖漏洞、
    CVE、GDPR/SOC2/数据留存、WCAG/a11y/i18n、license）。作为 L1 门禁段，由评审阶段与部署阶段在
    发布前调用，统一产出五态印章并 fail-closed：critical/high 必阻断部署。不新建顶层快照段，
    检查结果写入 snapshot.quality.verification_seals。
version: 1.0.0
family: pax
layer: L1
optional: true
requires_snapshot: true
status: active
---

# pax-gate

## Overview

发布前的质量/合规门禁段。聚合四类静态检查——**安全（SAST / 密钥 / 依赖漏洞）**、
**合规（GDPR / SOC2 / 数据留存 / 同意管理）**、**可访问性与国际化（WCAG / ARIA / a11y / i18n）**、
**许可证合规（GPL / AGPL 等）**——逐项给出判定与证据，写入 `snapshot.quality.verification_seals`，
并按 fail-closed 原则阻断 critical/high 缺陷的部署。本 skill 是 L1 门禁段，由上游评审阶段/部署阶段调用，
**不主动下探、不认领路由落点**。

## When to Use

- 引入新接口 / 依赖 / 前端 UI / 数据采集时，发布到用户可见环境前。
- 在评审阶段、部署前置检查阶段被调用。
- 涉及安全、合规、可访问性、许可证任一方面的改动。

## Common Pitfalls

- 把检查结果写成自由文本而非五态印章，导致下游无法机械消费。
- critical/high 缺陷仍放行部署（违反 fail-closed）。
- 检查项缺失证据或置信度说明。
- 与文档/判定（评审签名）职责混淆——本 skill 只产门禁结果，不替代评审签名。

## Verification Checklist

- [ ] 每项检查输出五态印章（verified / needs_fix / partial / blocked / needs_review）
- [ ] 每项印章附 evidence 列表与 confidence
- [ ] 存在 critical / high 缺陷时 `deployable: false`
- [ ] 写入 `snapshot.quality.verification_seals`，未新增顶层段
- [ ] 跳过检查时记录 `skip_reason`

## Execution Contract

- 前置门禁：需要完整快照或明确的检查范围（仓库 / 变更清单 / 目标环境）
- 未通过门禁：返回 `blocked`，列出缺失项，拒绝继续
- 版本检查：`pax-ops/versions.json`
- **fail-closed**：任一 critical / high 检查项未通过 → `deployable: false`，禁部署；不支持部分冻结
- 只读检查：不修改被测代码，只写 `snapshot.quality.verification_seals`（追加印章）
- 跳过留痕：任何跳过记录 `skip_reason`（跳过留痕契约）

## 职责边界

- 做什么：四类发布前静态检查（安全 / 合规 / a11y-i18n / 许可证），产出五态印章与可部署判定
- 不做什么：不修改被测代码、不认领路由落点、不替代评审签名、不引入新顶层快照段

## 输入

- 必需：`snapshot`（含目标仓库 / 变更清单 / 目标环境）
- 可选：`snapshot.infrastructure` 依赖清单、`snapshot.goal` 验收范围

## 工作流

### G1 检查范围判定（Scope Decision）

判定本次需要执行哪些检查类别：

```yaml
gate_scope:
  required: true
  categories:
    - security            # SAST / 密钥 / 依赖漏洞（变更含代码或依赖时必查）
    - compliance          # GDPR / SOC2 / 数据留存 / 同意管理（变更采集/存储用户数据时）
    - a11y_i18n           # WCAG / ARIA / 国际化（变更含 UI/前端时）
    - license             # 许可证合规（变更引入新依赖时）
  skip_reason: null
```

判定规则（查表）：
- 变更含代码 / 依赖 → `security: true`
- 变更含用户数据采集 / 存储 / 跨域 → `compliance: true`
- 变更含 UI / 前端 / 交互 → `a11y_i18n: true`
- 变更引入新第三方依赖 → `license: true`

### G2 分批检查（Check Execution）

逐类执行检查，每类产出若干检查项。检查项统一结构：

```yaml
check_item:
  id: "SEC-N+1"
  category: security
  severity: critical | high | medium | low
  summary: "<问题描述>"
  evidence: ["<文件:行号>", "<扫描器输出摘要>"]
  confidence: high | medium | low
```

严重度判定（查表）：
| 类别 | 严重度 | 示例 |
|---|---|---|
| security | critical | 硬编码密钥 / 已知 RCE 漏洞 / SAST 高危缺陷 |
| security | high | 依赖存在公开 CVE / 越权数据访问 |
| security | medium | 弱加密 / 缺输入校验 |
| compliance | high | 未获同意采集 PII / 数据留存超期 |
| compliance | medium | 缺少隐私声明 / 日志含冗余 PII |
| a11y_i18n | high | 表单无可访问性标签 / 对比度不达标 |
| a11y_i18n | medium | 缺 ARIA 状态 / 文案未国际化 |
| license | high | 引入 copyleft（GPL/AGPL）与专有代码冲突 |
| license | medium | 许可证缺失 / 兼容性存疑 |

### G3 门禁判定（Gate Verdict）

聚合所有检查项，输出可部署判定（fail-closed）：

```yaml
gate_verdict:
  deployable: false
  verdict: blocked
  blocking: ["SEC-01", "DEP-02"]   # critical/high 的检查项 id
  seal_results:
    - category: security
      result: blocked
    - category: compliance
      result: verified
    - category: a11y_i18n
      result: needs_fix
    - category: license
      result: verified
```

判表：
- 任一 `critical` / `high` 检查项 → `deployable: false`，`verdict: blocked`
- 仅 `medium` 项 → `deployable: true`，`verdict: needs_review`
- 全部 `low` / 无缺陷 → `deployable: true`，`verdict: verified`

### G4 印章写入（Seal Output）

把 G3 的逐类判定作为五态印章**追加**到 `snapshot.quality.verification_seals` 数组末位（复用既有段，
不新增顶层段；下游评审/部署阶段读取最后一条印章作为门禁结论）：

```yaml
seal:  # 追加到 snapshot.quality.verification_seals
  result: blocked          # verified | needs_fix | partial | blocked | needs_review
  summary: "门禁段发现 2 个 critical/high 缺陷，阻断部署"
  confidence: high
  evidence: ["SEC-01: 硬编码密钥", "DEP-02: 依赖 libX 存在 CVE-2024-xxxx"]
  attempts: 1
  duration: "PT30M"
```

## 输出契约

- `snapshot.quality.verification_seals`：追加一条五态印章（含 summary / confidence / evidence），
  供下游评审阶段/部署阶段消费
- `gate_scope`：本次覆盖的检查类别（含 `skip_reason` 若跳过）
- `gate_items`：全部检查项（id / category / severity / evidence / confidence）
- `gate_verdict`：`deployable` 布尔与 `verdict`（为便于下游机械消费，写入印章的 `evidence` 与
  `summary` 内，不单独新增顶层快照段）

## 失败模式

- 检查范围信息不足 → 返回 `blocked`，列出缺失项
- 扫描工具不可用 → 声明 `partial`，记录缺失证据，不得降级为 verified
- 发现 critical/high → 强制 `deployable: false`（fail-closed，不允许部分冻结）
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级

- 发现 critical/high 缺陷 → 阻断部署，交诊断阶段定位修复后再跑本门禁
- 合规高风险（GDPR/SOC2 触发）→ 交由多专家盲审阶段人工裁定
- 需要独立验证扫描结果 → 由主流程协调验证阶段
