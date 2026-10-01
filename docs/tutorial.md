# pax-* 教程

本文档提供 pax-* 家族的完整教程，包括如何添加新 Skill、如何评估等。

## 教程 1: 如何添加新 Skill

### 步骤 1: 创建 Skill 目录

```bash
mkdir skills/pax-<capability>
```

### 步骤 2: 创建 SKILL.md

```yaml
---
name: pax-<capability>
description: >
  <Skill 描述>
version: 0.2.0
family: pax
layer: L1
optional: true
requires_snapshot: true
---

# pax-<capability>

## Execution Contract
- 前置门禁：<前置条件>
- 未通过门禁：拒绝启动，返回上游阶段
- 版本检查：`pax-ops/versions.json`
- 禁止：<禁止事项>

## 职责边界
- 做什么：<职责>
- 不做什么：<非职责>

## 输入
- 必需：<必需输入>
- 可选：<可选输入>

## 工作流

### W1 <步骤 1>

```python
def step_1():
    """<步骤描述>"""
    
    # 实现逻辑
    pass
```

### W2 <步骤 2>

```python
def step_2():
    """<步骤描述>"""
    
    # 实现逻辑
    pass
```

## 输出契约
- <输出字段>

## 失败模式
- <失败情况> → <处理方式>

## 何时升级
- <升级条件> → <升级目标>
```

### 步骤 3: 更新 versions.json

```json
{
  "skills": {
    "pax-<capability>": "0.2.0"
  }
}
```

### 步骤 4: 更新 registry.json

```json
{
  "skills": [
    {
      "name": "pax-<capability>",
      "version": "0.2.0",
      "layer": "L1",
      "optional": true
    }
  ]
}
```

### 步骤 5: 验证

```bash
# 验证 Skill 格式
pax-forge validate skills/pax-<capability>

# 运行测试
pax-forge test
```

### 步骤 6: 提交

```bash
git add skills/pax-<capability>/
git add pax-ops/versions.json
git add pax-ops/registry.json
git commit -m "feat: 添加 pax-<capability> Skill"
```

---

## 教程 2: 如何评估 Skill

### 方法 1: 单元测试

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

### 方法 2: 契约测试

```bash
# 运行契约测试
pax-forge test
```

### 方法 3: 端到端测试

```bash
# 运行端到端测试
python opx-test/scenarios/<scenario>/run.py
```

### 方法 4: 集成测试

```bash
# 运行集成测试
python opx-test/scenarios/feature-dev-test/run.py
```

---

## 教程 3: 如何使用快照

### 快照结构

```yaml
meta:
  version: 1.0
  created_at: "ISO8601"
  updated_at: "ISO8601"
  skill_lineage: ["pax-orchestrate", "pax-clarify"]

goal:
  statement: "用户目标"
  success_criteria: []

consensus:
  required_precision: low
  dimensions:
    goal: unknown
    success_criteria: unknown
    constraints: unknown
    authorization: unknown
    exceptions: unknown
    terminology: unknown
  design_tree: []
  gaps_remaining: []

orchestration:
  intent:
    primary: "feature_dev"
    secondary: []
    classification_rationale: ""
  risk:
    irreversibility: 1
    impact_scope: 2
    uncertainty: 2
    coordination_cost: 1
    total: 6
    level: low
    forced_escalation: false
  diagnose_required: false
  route: ["clarify", "plan", "execute", "review"]
```

### 读取快照

```python
import yaml

with open("snapshot.yaml", "r") as f:
    snapshot = yaml.safe_load(f)

print(snapshot["orchestration"]["intent"]["primary"])
```

### 更新快照

```python
snapshot["consensus"]["dimensions"]["goal"] = "locked"
snapshot["meta"]["updated_at"] = "2026-10-01T17:00:00+08:00"

with open("snapshot.yaml", "w") as f:
    yaml.dump(snapshot, f, allow_unicode=True)
```

---

## 教程 4: 如何调试

### 查看快照文件

```bash
# 查看快照列表
ls opx-test/snapshots/

# 查看具体快照
cat opx-test/snapshots/snapshot_feature_dev_test.yaml
```

### 查看 Skill 调用链

```python
print(snapshot["meta"]["skill_lineage"])
```

### 查看执行日志

```python
print(snapshot["execution"]["logs"])
```

---

## 教程 5: 如何贡献

### 分支策略

- 主线：`main`，受保护
- 特性分支：`feat/<short-name>`
- 修复分支：`fix/<short-name>`

### 提交规范

使用 Conventional Commits：

```
<type>: <description>

[optional body]

[optional footer]
```

**类型**:
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `test`: 测试
- `chore`: 维护
- `refactor`: 重构

### PR 检查清单

- [ ] `pax-forge test` 通过
- [ ] 新增 skill 已注册到 `versions.json` 和 `registry.json`
- [ ] 如有 breaking change，`versions.json` 已 bump major
- [ ] 兼容矩阵已更新
- [ ] 文档同步

---

## 教程 6: 如何发布

### 版本管理

```bash
# 查看当前版本
pax-forge version

# 更新版本
pax-forge version patch  # 或 minor, major

# 生成发布说明
pax-forge release --dry-run
```

### 发布流程

```bash
# 1. 创建 release 分支
git checkout -b release/v0.3.0

# 2. 更新版本
pax-forge version minor

# 3. 更新 CHANGELOG
git add CHANGELOG.md

# 4. 提交
git commit -m "chore: release v0.3.0"

# 5. 创建 tag
git tag v0.3.0

# 6. 合并到 main
git checkout main
git merge release/v0.3.0

# 7. 推送
git push origin main
git push origin v0.3.0
```

---

## 参考

- [使用示例](./usage-examples.md)
- [设计文档](./pax-family-design.md)
- [贡献指南](../CONTRIBUTING.md)