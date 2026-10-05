# 贡献指南

感谢您对 pax-* 家族的贡献！本文档提供了详细的贡献指南。

## 目录

1. [如何新增一个 pax-* Skill](#如何新增一个-pax--skill)
2. [分支策略](#分支策略)
3. [提交规范](#提交规范)
4. [PR 检查清单](#pr-检查清单)
5. [代码规范](#代码规范)
6. [测试规范](#测试规范)
7. [文档规范](#文档规范)
8. [版本发布](#版本发布)

---

## 如何新增一个 pax-* Skill

### 步骤 1: 创建 Skill 骨架

使用 `pax-forge` 生成骨架：

```bash
pax-forge new pax-<capability> --layer <L0|L1|L2|L3|L4> [--optional]
```

**层级说明**:
- **L0**: 编排入口（如 pax-orchestrate）
- **L1**: 核心流程（如 pax-clarify, pax-diagnose）
- **L2**: 决策支持（如 pax-council, pax-advisor）
- **L3**: 执行工人（如 pax-worker-research）
- **L4**: 辅助工具（如 pax-verify, pax-evolve）

### 步骤 2: 编辑 SKILL.md

编辑 `skills/pax-<capability>/SKILL.md`：

```yaml
---
name: pax-<capability>
description: >
  <Skill 描述，说明何时使用此 Skill>
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---
```

**必需段落**:
- `## Execution Contract`: 执行契约
- `## 职责边界`: 职责边界
- `## 输入`: 输入要求
- `## 工作流`: 工作流步骤
- `## 输出契约`: 输出要求
- `## 失败模式`: 失败处理
- `## 何时升级`: 升级条件

### 步骤 3: 验证 Skill

```bash
# 验证 Skill 格式
pax-forge validate skills/pax-<capability>

# 运行契约测试
pax-forge test
```

### 步骤 4: 注册 Skill

更新 `pax-ops/versions.json`:

```json
{
  "skills": {
    "pax-<capability>": "0.2.0"
  }
}
```

更新 `pax-ops/registry.json`:

```json
{
  "skills": [
    {
      "name": "pax-<capability>",
      "version": "0.2.0",
      "layer": "L1",
      "optional": true,
      "description": "<Skill 描述>"
    }
  ]
}
```

### 步骤 5: 添加测试

在 `tests/` 目录添加测试文件：

```python
# tests/test_pax_<capability>.py

import pytest
from skills.pax_<capability> import Skill

def test_skill_initialization():
    """测试 Skill 初始化"""
    skill = Skill()
    assert skill.name == "pax-<capability>"

def test_skill_execution():
    """测试 Skill 执行"""
    skill = Skill()
    result = skill.execute(snapshot)
    assert result.status == "completed"
```

### 步骤 6: 更新文档

- 更新 `README.md`
- 添加使用示例到 `docs/usage-examples.md`
- 添加教程到 `docs/tutorial.md`

### 步骤 7: 提交

```bash
git add skills/pax-<capability>/
git add pax-ops/versions.json
git add pax-ops/registry.json
git add tests/
git add docs/
git add README.md

git commit -m "feat: 添加 pax-<capability> Skill"
```

---

## 分支策略

### 分支类型

| 分支 | 用途 | 命名规范 |
|------|------|----------|
| `main` | 主分支，受保护 | - |
| `feat/<name>` | 特性分支 | `feat/add-pax-monitor` |
| `fix/<name>` | 修复分支 | `fix/bug-123` |
| `release/vX.Y.Z` | 发布分支 | `release/v0.3.0` |

### 分支保护

- `main` 分支受保护，禁止直接推送
- 所有更改必须通过 PR 合并
- 需要至少 1 个 reviewer 批准

### 工作流程

```
1. 创建特性分支
   git checkout -b feat/add-pax-monitor

2. 开发并提交
   git add .
   git commit -m "feat: 添加 pax-monitor Skill"

3. 推送分支
   git push origin feat/add-pax-monitor

4. 创建 PR
   在 GitHub 创建 Pull Request

5. 合并 PR
   通过 CI 后合并到 main
```

---

## 提交规范

使用 Conventional Commits：

```
<type>: <description>

[optional body]

[optional footer]
```

### 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 pax-monitor Skill` |
| `fix` | 修复 | `fix: 修复 bug-123` |
| `docs` | 文档 | `docs: 更新 README` |
| `test` | 测试 | `test: 添加单元测试` |
| `chore` | 维护 | `chore: 更新依赖` |
| `refactor` | 重构 | `refactor: 重构代码` |
| `style` | 格式 | `style: 格式化代码` |
| `perf` | 性能 | `perf: 优化性能` |

### 示例

```
feat: 添加 pax-monitor Skill

- 支持运行中监控
- 支持告警触发
- 支持日志记录

Closes #123
```

---

## PR 检查清单

提交 PR 前，请确保：

- [ ] `pax-forge test` 通过
- [ ] 新增 skill 已注册到 `versions.json` 和 `registry.json`
- [ ] 如有 breaking change，`versions.json` 已 bump major
- [ ] 兼容矩阵已更新
- [ ] 文档同步
- [ ] 添加或更新测试
- [ ] 代码已格式化
- [ ] 无调试代码
- [ ] PR 描述清晰
- [ ] 关联相关 issue

---

## CI 门禁与外部工具

`pax-ci` 工作流包含 7 个 job。判定一个 job 是否真拦人，看两点：**触发条件**是否满足，
以及是否设了 `continue-on-error`。

| Job | 触发条件 | `continue-on-error` | 拦人? | 说明 |
|---|---|---|---|---|
| `contracts-and-tests` | 总是 | 否 | **是** | `pax-forge test` + `pytest` + 版本一致性校验 |
| `internal-routing-check` | 总是 | 否 | **是** | 内部路由数据集结构校验（`scripts/validate_internal_routing.py`） |
| `agentskills-ci-check` | 总是 | 否 | **是** | [agentskills-ci](https://github.com/damanisme/agentskills-ci) 对 `skills/` 打分，**每个 Skill 必须 ≥ 80/100** |
| `routing-eval` | `main` 或手动触发 | 否 | **是（仅 main）** | skillEval 路由评估；无 `DASHSCOPE_API_KEY` 时跳过 real 模式，只跑 mock |
| `quality-gate` | `vars.PAX_TOOLS_AVAILABLE == 'true'` | 否 | **默认不拦** | `tools/quality_gate.py` 五项检查 |
| `skilldiff-regression` | 总是 | **是** | 否（建议性） | 行为回归；失败只告警 |
| `quality-summary` | `always()` | 否 | 否 | 汇总 6 个 job 的结果到 Step Summary |

除 `quality-summary` 外，所有 job 都 `needs: contracts-and-tests`；`quality-summary` 需要全部 6 个。
因此 `contracts-and-tests` 一挂，其余全部变 `skipped`。

> 历史口径修正：此前本文与根 README 把 `routing-eval` 归为「硬门禁但默认跳过」，
> 并称 `internal-routing-check` 是「建议性」。两者都已不准确：
> `routing-eval` 现在不再依赖 `tools/`（见下），在 `main` 上默认执行；
> 而 `internal-routing-check` 没有 `continue-on-error`，失败会真的把 workflow 拖红。

### 0. 两个 job 的外部依赖

- **`routing-eval` 不再从 `tools/` 取工具**：它用第二次 `actions/checkout` 把同级仓库
  `sinvi/agent-skills-tooling` 以 `sparse-checkout: skillEval` 拉进检出目录再安装。
  所以它在 `main` 上默认**会执行**（mock 模式不需要 API Key；
  real 模式需 `secrets.DASHSCOPE_API_KEY`，未配置时该步自行跳过）。
- **`quality-gate` 仍依赖 `tools/quality_gate.py`**。而 `tools/` 被 `.gitignore` 忽略、
  **不在版本库中**，CI 检出里必然不存在，所以它的触发条件挂在仓库变量 `PAX_TOOLS_AVAILABLE` 上：

  - 未设置或不为 `'true'` → job 记为 `skipped`，`quality-summary` 会把它列入「以下检查本次未执行」；
  - 置为 `'true'` → job 先断言 `tools/quality_gate.py` 存在，缺失则 `::error` 直接失败，不静默放过。

  真正启用前需要先把工具 vendor 进版本库：

```bash
gh variable set PAX_TOOLS_AVAILABLE --repo opsbli/pax-skills --body "true"
```

> `skilldiff-regression` 若需要 recorded demo 的 trace 数据，同样来自 `tools/skilldiff/...`。
> 它设了 `continue-on-error: true`，内部检测到路径缺失时会跳过 demo 并在 Step Summary 写明「未在 CI 中执行」。

### 1. agentskills-ci 评分要求

本地实测中每个既有 Skill 均为 100/100；每个新 Skill 必须包含：

1. Frontmatter 必须含 `name` 和 `description` 字段
2. `description` 必须以 `Use when ...` / `When to use ...` / `Trigger ...` 开头（中文描述前缀即可）
3. Body 必须包含四个推荐段落（英文墓锚，中文内容）：
   - `## Overview`
   - `## When to Use`
   - `## Common Pitfalls`
   - `## Verification Checklist`
4. Verification Checklist 必须包含 checkbox 项（`- [ ]`）
5. 任何引用型路径（如 `references/foo.md`）必须在 Skill 目录内存在

本地验证（两种方式任选，输出一致）：

```bash
# 方式一：直接用外部工具
pip install agentskills-ci
agentskills-ci score ./skills --min-score 80 --format markdown

# 方式二：通过 pax-forge wrapper（推荐，CI 也走这条路径）
pip install -e .
python -m pax.forge.cli agentskills-ci --min-score 80
```

wrapper 优先使用 PATH 上的 `agentskills-ci` 二进制；如果没找到就回退到 `python -m agentskills_ci` 同解释器入口，因此本地开发环境即使 shell PATH 没刷新也能跑。

一键补齐（适用于现有 Skill）：

```bash
python scripts/backfill_agentskills_sections.py
```

该脚本会在 `# <skill-name>` 标题后插入四段推荐内容，并在 `description` 前缀上追加 `Use when: ` 触发词。

### 2. 开启 live skilldiff run（可选）

`skilldiff` 行为回归需要在真实 Agent harness 上运行，默认不开。要开启：

**方法一（推荐）：在 GitHub 仓库设置里添加一个 Secret**

- 仓库设置 → Settings → Secrets and variables → Actions
- 任选一个 harness，添加对应 Secret：
  - `ANTHROPIC_API_KEY` → Claude Code harness
  - `OPENAI_API_KEY` → Codex harness
  - `CODEBUFF_API_KEY` → Freebuff harness
- 可选：在 Settings → Variables → Actions 里设 `SKILLDIFF_HARNESS=claude`（或其他）强制指定；不设就自动探测。

**方法二：用 GitHub CLI 一键创建（需先 `gh auth login`）**

```bash
# 任选一个，把环境变量设为你的真实 API key：
gh secret set ANTHROPIC_API_KEY --repo opsbli/pax-skills --body "$ANTHROPIC_API_KEY"
gh secret set OPENAI_API_KEY    --repo opsbli/pax-skills --body "$OPENAI_API_KEY"
gh secret set CODEBUFF_API_KEY  --repo opsbli/pax-skills --body "$CODEBUFF_API_KEY"

# 可选：强制指定 harness
gh variable set SKILLDIFF_HARNESS --repo opsbli/pax-skills --body "claude"
```

**方法三：本地开发时手动跑一次**

```bash
npx skilldiff run evals/skilldiff/pax-clarify.scenario.yaml \
  --live --base origin/main --harness claude
```

**未配置时的行为**：job 不会阻塞 PR。CI 会自动跑一次 recorded-mode demo（使用 `tools/skilldiff/examples/traces/notes-helper-{old,new}.json`），把行为报告保存到 `evals/skilldiff/latest-recorded-report.md` 作为 artifact 上传，保证 pipeline 始终有东西可看。

> 附：`skilldiff orbit`（可视化 HTML）目前还不上 npm（源码在 `tools/skilldiff/src/orbit.ts`，但 dist 未包含）。本地开发时可以：
>
> ```bash
> cd tools/skilldiff && npm run build && npm link
> npx skilldiff orbit tools/skilldiff/examples/traces/notes-helper-old.json \
>                        tools/skilldiff/examples/traces/notes-helper-new.json \
>                        --out orbit.html
> ```

---

## 代码规范

### Python 代码

- 遵循 PEP 8
- 使用 type hints
- 添加 docstring
- 使用 `pytest` 进行单元测试

```python
from typing import List, Dict, Optional
import yaml

def load_snapshot(path: str) -> Dict:
    """加载快照文件
    
    Args:
        path: 快照文件路径
    
    Returns:
        快照数据
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
```

### YAML 配置

- 使用 2 空格缩进
- 避免行尾空格
- 使用引号包裹特殊字符

```yaml
meta:
  version: 1.0
  created_at: "2026-10-01T17:00:00+08:00"
```

### Skill 定义

- 遵循 pax-* 家族规范
- 包含完整的 Execution Contract
- 明确职责边界
- 定义清晰的输入输出契约

---

## 测试规范

### 测试类型

| 类型 | 位置 | 用途 |
|------|------|------|
| 单元测试 | `tests/test_*.py` | 测试单个模块 |
| 契约测试 | `pax-forge test` | 测试 11 条家族契约（含快照字段一致性、层成员一致性） |
| 能力评估 | `evals/` | 真实模型调用（外部路由 / 内部路由 / pax-diagnose）；运行方式见 `evals/README.md` |

### 测试命名

```python
def test_<action>_<condition>():
    """测试 <action> 在 <condition> 下"""
    pass
```

### 测试覆盖

- 核心逻辑覆盖率 ≥ 80%
- 边界条件必须测试
- 错误处理必须测试

---

## 文档规范

### 文档类型

| 类型 | 位置 | 用途 |
|------|------|------|
| README | `README.md` | 项目介绍 |
| 设计文档 | `docs/pax-family-design.md` | 详细设计 |
| 使用示例 | `docs/usage-examples.md` | 使用示例 |
| 教程 | `docs/tutorial.md` | 教程 |
| 贡献指南 | `CONTRIBUTING.md` | 贡献指南 |
| 变更日志 | `CHANGELOG.md` | 变更记录 |

### Markdown 规范

- 使用 ATX 标题（`#`）
- 使用 fenced code blocks
- 代码块指定语言
- 列表使用 2 空格缩进

### Skill 文档

每个 Skill 的 `SKILL.md` 必须包含：

- frontmatter（name, description, version, family, layer, optional, requires_snapshot）
- Execution Contract
- 职责边界
- 输入
- 工作流
- 输出契约
- 失败模式
- 何时升级

---

## 版本发布

### 版本管理

使用语义化版本（SemVer）：

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: 不兼容的 API 更改
- **MINOR**: 向下兼容的功能新增
- **PATCH**: 向下兼容的问题修复

### 发布流程

```bash
# 1. 创建 release 分支
git checkout -b release/v0.3.0

# 2. 更新版本
pax-forge version minor

# 3. 更新 CHANGELOG
# 编辑 CHANGELOG.md

# 4. 提交
git add .
git commit -m "chore: release v0.3.0"

# 5. 创建 tag
git tag v0.3.0

# 6. 合并到 main
git checkout main
git merge release/v0.3.0

# 7. 推送
git push origin main
git push origin v0.3.0

# 8. 创建 GitHub Release
# 在 GitHub 创建 Release
```

### CHANGELOG 格式

使用 Keep a Changelog：

```markdown
## [0.3.0] - 2026-10-01

### Added
- 添加 pax-monitor Skill
- 添加 pax-rollback Skill

### Changed
- 更新 pax-orchestrate 路由规则

### Fixed
- 修复 bug-123
```

---

## 获得帮助

如果遇到困难，可以通过以下方式获得帮助：

1. **查看文档**: [docs/](./docs/)
2. **查看评估与用法示例**: [evals/](./evals/) 与 [docs/usage-examples.md](./docs/usage-examples.md)
3. **创建 Issue**: 在 GitHub 创建 Issue
4. **提交 PR**: 提交 Pull Request

---

## 许可证

本项目使用 MIT 许可证。