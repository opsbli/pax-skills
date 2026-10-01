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
| 契约测试 | `pax-forge test` | 测试家族契约 |
| 集成测试 | `opx-test/scenarios/` | 测试完整流程 |
| 端到端测试 | `opx-test/scenarios/` | 测试真实场景 |

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
2. **查看示例**: [opx-test/scenarios/](../opx-test/scenarios/)
3. **创建 Issue**: 在 GitHub 创建 Issue
4. **提交 PR**: 提交 Pull Request

---

## 许可证

本项目使用 MIT 许可证。