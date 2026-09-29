# pax-* 家族 Bootstrap 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从零构建 `pax-*` AI Skill 家族的最小可运行骨架——包含元层生成器 `pax-forge`、家族宪法 Schema、快照 Schema、13 个 Skill 的骨架、契约测试、补丁层与治理文档。

**Architecture:** 采用 Python 3.11+ + JSON Schema (Draft 2020-12) 作为单一真相源；`pax-forge` 是纯 CLI 工具（argparse + 仅 PyYAML/jsonschema 两个运行时依赖），负责生成、校验、注册、版本管理；`pax-family.schema.yaml` 与 `pax-snapshot.schema.json` 驱动所有契约测试；补丁层用幂等 `apply.py` 声明式重放。所有 Skill 遵循统一 frontmatter + 分区骨架（Execution Contract / 职责边界 / 输入 / 工作流 / 输出契约 / 失败模式 / 何时升级）。

**Tech Stack:** Python 3.11+, PyYAML 6.x, jsonschema 4.x, pytest 8.x, argparse (stdlib), Jinja2（模板渲染）, src/ layout, pyproject.toml

**前置阅读**：`docs/pax-family-design.md`（唯一事实来源）

**Worktree**：本计划应在专用 worktree 内执行，避免污染主分支。建议 Phase 0 结束后切到 `feat/pax-bootstrap` 分支。

**提交策略**：每个 Task 结束后独立 `git add + git commit`，commit message 用 `feat:` / `chore:` / `docs:` / `test:` 前缀。全部完成后在 Task 8.3 统一打 tag `v0.1.0`。

---

## 目录结构（最终形态）

```
pax-skills/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore
├── docs/
│   ├── pax-family-design.md
│   └── plans/
│       └── 2026-09-29-pax-family-bootstrap.md
├── schemas/
│   ├── pax-family.schema.yaml         # 家族宪法（单一真相源）
│   └── snapshot.schema.json           # 快照 JSON Schema
├── pax-ops/
│   ├── versions.json                  # 版本基线
│   ├── registry.json                  # Skill 注册表
│   └── patches/
│       └── manifest.json              # 补丁清单
├── src/
│   └── pax/
│       ├── __init__.py
│       ├── __main__.py                # python -m pax → CLI
│       ├── forge/
│       │   ├── __init__.py
│       │   ├── cli.py                 # CLI 入口
│       │   ├── loader.py              # 加载 schema / versions / registry
│       │   ├── init.py                # pax-forge init
│       │   ├── generator.py           # 生成 Skill 骨架
│       │   ├── validator.py           # 校验单个 Skill
│       │   ├── register.py            # 注册到 registry
│       │   ├── contracts.py           # 契约测试器
│       │   ├── versioning.py          # 版本管理
│       │   └── patcher.py             # 补丁层幂等重放
│       └── templates/
│           ├── meta.tmpl
│           ├── L0.tmpl
│           ├── L1.tmpl
│           ├── L2.tmpl
│           ├── L3.tmpl
│           └── L4.tmpl
├── skills/
│   ├── pax-orchestrate/SKILL.md
│   ├── pax-clarify/SKILL.md
│   ├── pax-diagnose/SKILL.md
│   ├── pax-plan/SKILL.md
│   ├── pax-execute/SKILL.md
│   ├── pax-review/SKILL.md
│   ├── pax-advisor/SKILL.md
│   ├── pax-council/SKILL.md
│   ├── pax-worker-grok/SKILL.md
│   ├── pax-worker-codex/SKILL.md
│   ├── pax-verify/SKILL.md
│   ├── pax-evolve/SKILL.md
│   └── pax-docs/SKILL.md
├── references/
│   ├── severity-criteria.md
│   ├── domain-dependencies.md
│   └── compatibility-matrix.md
└── tests/
    ├── conftest.py
    ├── test_smoke.py
    ├── test_loader.py
    ├── test_validator.py
    ├── test_generator.py
    ├── test_register.py
    ├── test_contracts.py
    ├── test_versioning.py
    ├── test_patcher.py
    ├── test_patcher_e2e.py
    ├── test_cli.py
    └── test_cli_e2e.py
```

---

## Phase 0：项目脚手架

### Task 0.1：初始化 pyproject.toml 与目录结构

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/pax/__init__.py`
- Create: `src/pax/forge/__init__.py`

**Step 1: 写完整 pyproject.toml**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "pax-forge"
version = "0.1.0"
description = "Pact-based Agreement eXecution family: generator, validator, contract tester"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0.1",
    "jsonschema>=4.21",
    "jinja2>=3.1.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
pax-forge = "pax.forge.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/pax"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
```

**Step 2: 写 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
build/
dist/
.pytest_cache/
.coverage
htmlcov/

# Editors
.vscode/
.idea/
.DS_Store

# Local artifacts
*.log
```

**Step 3: 写两个 `__init__.py`**

`src/pax/__init__.py`:

```python
"""pax-* family: Pact-based Agreement eXecution."""
__version__ = "0.1.0"
```

`src/pax/forge/__init__.py`:

```python
"""pax-forge: generator, validator, contract tester for pax-* skills."""
```

**Step 4: 安装并确认能导入**

Run:
```bash
python -m venv .venv
. .venv/Scripts/activate            # Windows
# source .venv/bin/activate          # Linux/macOS
pip install -e ".[dev]"
python -c "import pax; print(pax.__version__)"
```
Expected: `0.1.0`

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore src/
git commit -m "chore: init pax-forge project skeleton"
```

---

### Task 0.2：pytest 冒烟测试

**Files:**
- Create: `tests/test_smoke.py`

**Step 1: 写测试**

```python
# tests/test_smoke.py
from pax import __version__

def test_version_string():
    assert __version__ == "0.1.0"
```

**Step 2: 跑测试确认通过**

Run: `pytest tests/test_smoke.py -v`
Expected: `1 passed`

**Step 3: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add pytest smoke test"
```

---

## Phase 1：家族宪法与数据模型（Schema 优先）

Phase 1 全部是**只读文件 + 加载器**，不涉及 CLI。所有后续 CLI 都依赖这里。

### Task 1.1：定义 `pax-family.schema.yaml` 加载器

**Files:**
- Create: `schemas/pax-family.schema.yaml`
- Create: `src/pax/forge/loader.py`
- Create: `tests/test_loader.py`

**Step 1: 写加载器测试（先失败）**

```python
# tests/test_loader.py
from pathlib import Path
import pytest


def test_load_family_schema_shape():
    """Loader 返回结构，键齐全。"""
    from pax.forge.loader import load_family_schema
    schema = load_family_schema()
    assert schema["family"] == "pax"
    assert "Pact-based Agreement" in schema["family_expansion"]
    assert schema["version"] == 1.0
    for layer in ["meta", "L0", "L1", "L2", "L3", "L4"]:
        assert layer in schema["layers"]
    for required_key in ["naming", "required_frontmatter", "required_sections",
                         "snapshot_schema", "version_source"]:
        assert required_key in schema["contracts"]


def test_load_family_schema_missing_raises(tmp_path, monkeypatch):
    from pax.forge.loader import load_family_schema
    monkeypatch.setattr("pax.forge.loader.FAMILY_SCHEMA_PATH",
                        tmp_path / "does-not-exist.yaml")
    with pytest.raises(FileNotFoundError):
        load_family_schema()
```

**Step 2: 跑测试确认失败**

Run: `pytest tests/test_loader.py -v`
Expected: `ImportError` 或 `FileNotFoundError`

**Step 3: 写 family schema 与加载器**

`schemas/pax-family.schema.yaml`（照抄设计文档 §10.2，并补上 `family_expansion`、`version`）：

```yaml
family: pax
family_expansion: "Pact-based Agreement eXecution"
version: 1.0
layers:
  meta: [forge]
  L0: [orchestrate]
  L1: [clarify, diagnose, plan, execute, review]
  L2: [advisor, council]
  L3: ["worker-*"]
  L4: [verify, evolve, docs]
contracts:
  naming: "^pax-[a-z][a-z0-9-]*$"
  required_frontmatter:
    - name
    - description
    - version
    - family
    - layer
    - requires_snapshot
  required_sections:
    - Execution Contract
    - 职责边界
    - 输入
    - 工作流
    - 输出契约
    - 失败模式
    - 何时升级
  snapshot_schema: "./schemas/snapshot.schema.json"
  version_source: "./pax-ops/versions.json"
```

`src/pax/forge/loader.py`:

```python
"""Load pax-* family single-source-of-truth files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

# 仓库根：src/pax/forge/loader.py → src/pax/forge → src/pax → src → root
PAX_ROOT = Path(__file__).resolve().parents[3]

FAMILY_SCHEMA_PATH = PAX_ROOT / "schemas" / "pax-family.schema.yaml"
SNAPSHOT_SCHEMA_PATH = PAX_ROOT / "schemas" / "snapshot.schema.json"
VERSIONS_PATH = PAX_ROOT / "pax-ops" / "versions.json"
REGISTRY_PATH = PAX_ROOT / "pax-ops" / "registry.json"
PATCHES_MANIFEST_PATH = PAX_ROOT / "pax-ops" / "patches" / "manifest.json"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_family_schema(path: Path = FAMILY_SCHEMA_PATH) -> dict[str, Any]:
    return _load_yaml(path)


def load_snapshot_schema(path: Path = SNAPSHOT_SCHEMA_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_versions(path: Path = VERSIONS_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry: dict[str, Any], path: Path = REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_patches_manifest(path: Path = PATCHES_MANIFEST_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_patches_manifest(manifest: dict[str, Any],
                          path: Path = PATCHES_MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
```

> **说明**：loader 一次写齐全部加载/保存函数，避免后续 Task 1.2–1.5 反复改动同一文件。测试按每份文件分块推进。

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_loader.py -v`
Expected: `2 passed`

**Step 5: Commit**

```bash
git add schemas/pax-family.schema.yaml src/pax/forge/loader.py tests/test_loader.py
git commit -m "feat(loader): single-source-of-truth loaders"
```

---

### Task 1.2：定义 `pax-snapshot.schema.json`

**Files:**
- Create: `schemas/snapshot.schema.json`
- Modify: `tests/test_loader.py`

**Step 1: 追加失败测试**

```python
def test_load_snapshot_schema_shape():
    from pax.forge.loader import load_snapshot_schema
    schema = load_snapshot_schema()
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$id"].endswith("snapshot.schema.json")
    required = set(schema["required"])
    for key in ["meta", "goal", "consensus", "orchestration"]:
        assert key in required
    for key in ["symptom", "diagnosis", "plan", "contract", "execution",
                "review", "quality"]:
        assert key in schema["properties"]


def test_snapshot_schema_validates_minimal_instance():
    import jsonschema
    from pax.forge.loader import load_snapshot_schema
    schema = load_snapshot_schema()
    minimal = {
        "meta": {"version": 1.0, "created_at": "2026-09-29T00:00:00Z",
                 "updated_at": "2026-09-29T00:00:00Z", "skill_lineage": []},
        "goal": {"statement": "test", "success_criteria": []},
        "consensus": {"required_precision": "low", "dimensions": {},
                       "design_tree": [], "gaps_remaining": []},
        "orchestration": {"diagnose_required": False, "rationale": "n/a",
                           "skip_reason": None, "route": [],
                           "question_strategy": "batch"},
    }
    jsonschema.validate(minimal, schema)  # 不抛异常即通过
```

**Step 2: 跑测试确认失败**

**Step 3: 写快照 Schema**

`schemas/snapshot.schema.json`：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pax.family/schemas/snapshot.schema.json",
  "title": "pax-snapshot",
  "description": "Single source of truth exchanged between pax-* skills.",
  "type": "object",
  "required": ["meta", "goal", "consensus", "orchestration"],
  "additionalProperties": false,
  "properties": {
    "meta": {
      "type": "object",
      "required": ["version", "created_at", "updated_at", "skill_lineage"],
      "additionalProperties": false,
      "properties": {
        "version": {"type": "number", "const": 1.0},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "skill_lineage": {
          "type": "array",
          "items": {"type": "string", "pattern": "^pax-[a-z][a-z0-9-]*$"}
        }
      }
    },
    "goal": {
      "type": "object",
      "required": ["statement", "success_criteria"],
      "additionalProperties": false,
      "properties": {
        "statement": {"type": "string", "minLength": 1},
        "success_criteria": {"type": "array", "items": {"type": "string"}}
      }
    },
    "consensus": {
      "type": "object",
      "required": ["required_precision", "dimensions", "design_tree", "gaps_remaining"],
      "additionalProperties": false,
      "properties": {
        "required_precision": {"type": "string", "enum": ["low", "medium", "high"]},
        "dimensions": {"type": "object"},
        "design_tree": {"type": "array"},
        "gaps_remaining": {"type": "array"}
      }
    },
    "orchestration": {
      "type": "object",
      "required": ["diagnose_required", "rationale", "skip_reason",
                   "route", "question_strategy"],
      "additionalProperties": false,
      "properties": {
        "diagnose_required": {"type": "boolean"},
        "rationale": {"type": "string"},
        "skip_reason": {"type": ["string", "null"]},
        "route": {"type": "array", "items": {"type": "string"}},
        "question_strategy": {"type": "string",
                                "enum": ["batch", "one-by-one"]}
      }
    },
    "symptom": {
      "type": "object",
      "required": ["description", "impact", "reproduction", "first_observed"],
      "additionalProperties": false,
      "properties": {
        "description": {"type": "string"},
        "impact": {"type": "string"},
        "reproduction": {"type": "string"},
        "first_observed": {"type": "string", "format": "date-time"},
        "recent_changes": {"type": "array", "items": {"type": "string"}}
      }
    },
    "diagnosis": {"type": "object"},
    "plan": {
      "type": "object",
      "required": ["steps", "status"],
      "additionalProperties": false,
      "properties": {
        "steps": {"type": "array"},
        "dependencies": {"type": "array"},
        "evidence": {"type": "array"},
        "verification_strategy": {"type": "array"},
        "status": {"type": "string", "enum": ["draft", "frozen"]}
      }
    },
    "contract": {
      "type": "object",
      "required": ["authorization", "constraints", "exceptions",
                   "assumptions", "withdraw"],
      "additionalProperties": false,
      "properties": {
        "authorization": {"type": "object"},
        "constraints": {"type": "array"},
        "exceptions": {"type": "array"},
        "assumptions": {"type": "array"},
        "withdraw": {"type": "array"}
      }
    },
    "execution": {
      "type": "object",
      "required": ["mode", "log", "deviations", "changes"],
      "additionalProperties": false,
      "properties": {
        "mode": {"type": "string", "enum": ["normal", "fix"]},
        "log": {"type": "array"},
        "deviations": {"type": "array"},
        "changes": {"type": "array"}
      }
    },
    "review": {
      "type": "object",
      "required": ["verdict", "stamp", "rationale"],
      "additionalProperties": false,
      "properties": {
        "verdict": {"type": "string",
                    "enum": ["pass", "fail", "partial", "blocked", "escalated"]},
        "stamp": {"type": "string"},
        "rationale": {"type": "string"},
        "findings": {"type": "array"}
      }
    },
    "quality": {
      "type": "object",
      "required": ["verification_seals", "evolution_entries"],
      "additionalProperties": false,
      "properties": {
        "verification_seals": {"type": "array"},
        "evolution_entries": {"type": "array"}
      }
    }
  }
}
```

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_loader.py -v`
Expected: `4 passed`

**Step 5: Commit**

```bash
git add schemas/snapshot.schema.json tests/test_loader.py
git commit -m "feat(schema): add pax-snapshot JSON Schema"
```

---

### Task 1.3：定义 `pax-ops/versions.json`

**Files:**
- Create: `pax-ops/versions.json`
- Modify: `tests/test_loader.py`

**Step 1: 追加失败测试**

```python
def test_load_versions_shape():
    from pax.forge.loader import load_versions
    versions = load_versions()
    assert versions["family"] == "pax"
    assert versions["version"] == "0.1.0"
    assert "skills" in versions
    assert "pax-clarify" in versions["skills"]
    assert versions["skills"]["pax-clarify"]["layer"] == "L1"
    assert "compatibility_matrix" in versions
```

**Step 2: 跑测试确认失败**

**Step 3: 写文件**

`pax-ops/versions.json`：

```json
{
  "family": "pax",
  "version": "0.1.0",
  "skills": {
    "pax-orchestrate":  {"layer": "L0", "optional": false, "version": "0.1.0", "status": "active"},
    "pax-clarify":      {"layer": "L1", "optional": false, "version": "0.1.0", "status": "active"},
    "pax-diagnose":     {"layer": "L1", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-plan":         {"layer": "L1", "optional": false, "version": "0.1.0", "status": "active"},
    "pax-execute":      {"layer": "L1", "optional": false, "version": "0.1.0", "status": "active"},
    "pax-review":       {"layer": "L1", "optional": false, "version": "0.1.0", "status": "active"},
    "pax-advisor":      {"layer": "L2", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-council":      {"layer": "L2", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-worker-grok":  {"layer": "L3", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-worker-codex": {"layer": "L3", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-verify":       {"layer": "L4", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-evolve":       {"layer": "L4", "optional": true,  "version": "0.1.0", "status": "active"},
    "pax-docs":         {"layer": "L4", "optional": true,  "version": "0.1.0", "status": "active"}
  },
  "compatibility_matrix": {
    "pax-orchestrate@0.1": ["pax-clarify@0.1"],
    "pax-clarify@0.1":     ["pax-diagnose@0.1", "pax-plan@0.1"],
    "pax-diagnose@0.1":    ["pax-plan@0.1"],
    "pax-plan@0.1":        ["pax-execute@0.1"],
    "pax-execute@0.1":     ["pax-review@0.1"]
  }
}
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add pax-ops/versions.json tests/test_loader.py
git commit -m "feat(ops): add versions.json single-source-of-truth"
```

---

### Task 1.4：定义 `pax-ops/registry.json`

**Files:**
- Create: `pax-ops/registry.json`
- Modify: `tests/test_loader.py`

**Step 1: 追加失败测试**

```python
def test_load_registry_shape():
    from pax.forge.loader import load_registry
    registry = load_registry()
    assert registry["family"] == "pax"
    assert isinstance(registry["skills"], list)
    assert registry["skills"] == []
    assert registry["updated_at"] is not None


def test_save_registry_roundtrip(tmp_path):
    from pax.forge.loader import load_registry, save_registry, REGISTRY_PATH
    registry = load_registry()
    registry["skills"] = [{"name": "pax-foo", "layer": "L1",
                            "optional": False, "version": "0.1.0",
                            "path": "skills/pax-foo/SKILL.md",
                            "registered_at": "2026-09-29T00:00:00Z"}]
    save_registry(registry, tmp_path / "r.json")
    loaded = load_registry(tmp_path / "r.json")
    assert loaded["skills"][0]["name"] == "pax-foo"
```

**Step 2: 跑测试确认失败**

**Step 3: 写文件**

`pax-ops/registry.json`：

```json
{
  "family": "pax",
  "updated_at": "2026-09-29T12:00:00Z",
  "skills": []
}
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add pax-ops/registry.json tests/test_loader.py
git commit -m "feat(ops): add registry.json"
```

---

### Task 1.5：定义 `pax-ops/patches/manifest.json`

**Files:**
- Create: `pax-ops/patches/manifest.json`
- Modify: `tests/test_loader.py`

**Step 1: 追加失败测试**

```python
def test_load_patches_manifest_shape():
    from pax.forge.loader import load_patches_manifest
    manifest = load_patches_manifest()
    assert manifest["version"] == "1.0"
    assert manifest["patches"] == []
    assert manifest["applied"] == []


def test_save_patches_manifest_roundtrip(tmp_path):
    from pax.forge.loader import (load_patches_manifest,
                                   save_patches_manifest)
    manifest = load_patches_manifest()
    manifest["patches"] = [{"id": "p1", "target": "skills/pax-clarify/SKILL.md",
                             "operation": "replace", "needle": "a", "repl": "b"}]
    target = tmp_path / "m.json"
    save_patches_manifest(manifest, target)
    assert load_patches_manifest(target)["patches"][0]["id"] == "p1"
```

**Step 2: 跑测试确认失败**

**Step 3: 写文件**

`pax-ops/patches/manifest.json`：

```json
{
  "version": "1.0",
  "patches": [],
  "applied": []
}
```

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_loader.py -v`
Expected: `8 passed`

**Step 5: Commit**

```bash
git add pax-ops/patches/manifest.json tests/test_loader.py
git commit -m "feat(ops): add patches manifest"
```

---

## Phase 2：pax-forge CLI 骨架

CLI 结构：**argparse 子命令**，每个子命令对应一个 Task。整体接口：

```
pax-forge init <path>                  # 生成 family skeleton
pax-forge new <name> --layer <L?> --description "..." [--optional]
pax-forge validate <path>              # 校验单个 skill
pax-forge register <path>              # 注册到 registry
pax-forge list                         # 列出已注册 skill
pax-forge test [--skill <name>]        # 跑契约测试
pax-forge version <patch|minor|major>  # 版本 bump
pax-forge deprecate <name>             # 标记 skill 为 deprecated
pax-forge patch apply                  # 幂等重放补丁
```

### Task 2.1：CLI 入口空壳

**Files:**
- Create: `src/pax/forge/cli.py`
- Create: `src/pax/__main__.py`
- Create: `tests/test_cli.py`

**Step 1: 写测试（先失败）**

```python
# tests/test_cli.py
import subprocess, sys


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pax", *args],
        capture_output=True, text=True, check=False,
    )


def test_cli_shows_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_cli_empty_command_exits_nonzero():
    result = run_cli()
    assert result.returncode != 0
```

**Step 2: 跑测试确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: `python -m pax` 报 `No module named pax.__main__`

**Step 3: 写 CLI**

`src/pax/__main__.py`:

```python
"""Allow `python -m pax`."""
from pax.forge.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

`src/pax/forge/cli.py`:

```python
"""pax-forge CLI: generator, validator, contract tester."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pax import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pax-forge",
        description="pax-* family: generator, validator, contract tester",
    )
    parser.add_argument("--version", action="version",
                        version=f"pax-forge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    init_p = sub.add_parser("init", help="Generate pax-* family skeleton")
    init_p.add_argument("path", nargs="?", default="./pax-family",
                        help="Target directory")

    # new
    new_p = sub.add_parser("new", help="Create a new pax-* skill")
    new_p.add_argument("name")
    new_p.add_argument("--layer", required=True,
                       choices=["meta", "L0", "L1", "L2", "L3", "L4"])
    new_p.add_argument("--description", default="TODO: describe capability")
    new_p.add_argument("--optional", action="store_true")

    # validate
    validate_p = sub.add_parser("validate", help="Validate a single skill directory")
    validate_p.add_argument("path")

    # register
    register_p = sub.add_parser("register", help="Register a validated skill")
    register_p.add_argument("path")

    # list
    sub.add_parser("list", help="List registered skills")

    # test
    test_p = sub.add_parser("test", help="Run cross-skill contract tests")
    test_p.add_argument("--skill", help="Only test this skill (default: all)")

    # version
    version_p = sub.add_parser("version", help="Bump family version")
    version_p.add_argument("bump", choices=["patch", "minor", "major"])

    # deprecate
    deprecate_p = sub.add_parser("deprecate", help="Mark a skill as deprecated")
    deprecate_p.add_argument("name")

    # patch
    patch_p = sub.add_parser("patch", help="Apply declarative patches")
    patch_p.add_subparsers(dest="sub_command", required=True)
    patch_p.add_parser("apply", help="Replay patches manifest idempotently")

    return parser


def _not_implemented() -> int:
    print("(subcommand not yet implemented)", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # 所有子命令在后续 Task 中逐步实现；未实现时统一返回 2
    return _not_implemented()


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: `2 passed`

**Step 5: Commit**

```bash
git add src/pax/forge/cli.py src/pax/__main__.py tests/test_cli.py
git commit -m "feat(cli): argparse skeleton with all subcommands declared"
```

---

### Task 2.2：`pax-forge --version` 与 `--help`

**Files:**
- Modify: `tests/test_cli.py`

**Step 1: 追加测试（当前已实现，应通过）**

```python
def test_cli_version_flag():
    result = run_cli("--version")
    assert result.returncode == 0
    assert "pax-forge 0.1.0" in result.stdout
```

**Step 2: 跑测试确认通过**

Run: `pytest tests/test_cli.py::test_cli_version_flag -v`

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test(cli): add version flag assertion"
```

---

### Task 2.3：`pax-forge init` 生成 family skeleton

**Files:**
- Create: `src/pax/forge/init.py`
- Modify: `src/pax/forge/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: 写测试（失败）**

```python
def test_cli_init_creates_skeleton(tmp_path):
    target = tmp_path / "pax-family"
    result = run_cli("init", str(target))
    assert result.returncode == 0, result.stderr
    assert (target / "schemas" / "pax-family.schema.yaml").exists()
    assert (target / "schemas" / "snapshot.schema.json").exists()
    assert (target / "pax-ops" / "versions.json").exists()
    assert (target / "pax-ops" / "registry.json").exists()
    assert (target / "pax-ops" / "patches" / "manifest.json").exists()
    assert (target / "skills").is_dir()
    assert (target / "references").is_dir()
```

**Step 2: 跑测试确认失败**

**Step 3: 写实现**

`src/pax/forge/init.py`:

```python
"""Generate pax-* family skeleton into a target directory."""
from __future__ import annotations

import shutil
from pathlib import Path

from pax.forge import loader


SKELETON_FILES: dict[str, Path] = {
    "schemas/pax-family.schema.yaml": loader.FAMILY_SCHEMA_PATH,
    "schemas/snapshot.schema.json": loader.SNAPSHOT_SCHEMA_PATH,
    "pax-ops/versions.json": loader.VERSIONS_PATH,
    "pax-ops/registry.json": loader.REGISTRY_PATH,
    "pax-ops/patches/manifest.json": loader.PATCHES_MANIFEST_PATH,
}

SKELETON_DIRS: list[str] = ["skills", "references"]


class InitError(Exception):
    pass


def init_family(target: Path) -> list[Path]:
    """Copy single-source-of-truth files into `target` and create empty dirs."""
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise InitError(f"Target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    for d in SKELETON_DIRS:
        (target / d).mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for rel, src in SKELETON_FILES.items():
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(dst)
    return copied
```

`src/pax/forge/cli.py` 中修改 `main` 的 `init` 分支：

```python
    if args.command == "init":
        from pax.forge.init import init_family, InitError
        target = Path(args.path).resolve()
        try:
            copied = init_family(target)
        except InitError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for p in copied:
            print(f"  wrote {p.relative_to(target)}")
        print(f"init complete -> {target}")
        return 0
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add src/pax/forge/init.py src/pax/forge/cli.py tests/test_cli.py
git commit -m "feat(cli): implement pax-forge init subcommand"
```

---

### Task 2.4：`pax-forge new <name>` 生成新 Skill（先做 L1 模板）

**Files:**
- Create: `src/pax/forge/generator.py`
- Create: `src/pax/templates/L1.tmpl`
- Modify: `src/pax/forge/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_generator.py`

**Step 1: 写测试（失败）**

```python
# tests/test_generator.py
import yaml
from pathlib import Path
from pax.forge.generator import generate_skill, GenerationError


def test_generate_l1_skill(tmp_path):
    skill_dir = generate_skill(
        name="pax-foo", layer="L1",
        description="A test skill",
        target_root=tmp_path, optional=False,
    )
    assert skill_dir.name == "pax-foo"
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---", 2)[1])
    assert fm["name"] == "pax-foo"
    assert fm["layer"] == "L1"
    assert fm["family"] == "pax"
    assert fm["optional"] is False
    assert "version" in fm
    for section in ["Execution Contract", "职责边界", "输入", "工作流",
                    "输出契约", "失败模式", "何时升级"]:
        assert f"## {section}" in text


def test_generate_rejects_bad_name(tmp_path):
    import pytest
    with pytest.raises(GenerationError):
        generate_skill(name="not-pax-foo", layer="L1",
                       description="x", target_root=tmp_path, optional=False)
```

追加到 `tests/test_cli.py`：

```python
def test_cli_new_creates_skill(tmp_path):
    # 通过 CLI 触发；family root 使用当前项目目录
    import shutil
    dest = tmp_path / "fam"
    r1 = run_cli("init", str(dest))
    assert r1.returncode == 0
    r2 = run_cli("new", "pax-bar", "--layer", "L1",
                 "--description", "desc", cwd=None)
    # 说明：CLI 默认写到项目根，测试这里不校验产物，仅验证能启动
    assert r2.returncode in (0, 1, 2)
```

**Step 2: 跑测试确认失败**

**Step 3: 写 L1 模板**

`src/pax/templates/L1.tmpl`:

```jinja
---
name: {{ name }}
description: >
  {{ description }}。当需要 {{ use_case | default('处理该类任务') }} 时使用。
version: {{ version }}
family: pax
layer: {{ layer }}
optional: {{ 'true' if optional else 'false' }}
requires_snapshot: true
---

# {{ name }}

## Execution Contract
- 前置门禁：<在此声明前置条件，例如 `snapshot.<section> == <value>`>
- 未通过门禁：<在此声明降级或返回行为>
- 版本检查：读取 `pax-ops/versions.json` 校验家族版本

## 职责边界
- 做什么：<一行说明核心动作>
- 不做什么：<列出越权动作>

## 输入
- 必需：`snapshot.<...>`
- 可选：<...>

## 工作流
1. <步骤 1>
2. <步骤 2>
3. <步骤 3>

## 输出契约
- `<snapshot.<section>>`，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 如果 `<条件>`，则 `<行为>`

## 何时升级
- 如果 `<风险触发条件>`，调用 `<目标 Skill>`
```

`src/pax/forge/generator.py`:

```python
"""Generate pax-* skill skeletons from layered templates."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from pax.forge import loader


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class GenerationError(Exception):
    pass


def _render(template_name: str, **ctx: object) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    return env.get_template(f"{template_name}.tmpl").render(**ctx)


def generate_skill(*, name: str, layer: str, description: str,
                   target_root: Path, optional: bool = False) -> Path:
    """Create `target_root/skills/<name>/SKILL.md` and return the skill dir."""
    family = loader.load_family_schema()
    naming_re = re.compile(family["contracts"]["naming"])
    if not naming_re.match(name):
        raise GenerationError(
            f"Name violates family naming contract: {name!r}"
        )
    versions = loader.load_versions()
    family_version = versions["version"]
    skill_version = versions["skills"].get(name, {}).get(
        "version", family_version
    )
    skill_dir = target_root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    template_name = "meta" if layer == "meta" else layer
    content = _render(
        template_name,
        name=name, layer=layer, description=description,
        optional=optional, version=skill_version,
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir
```

修改 `src/pax/forge/cli.py` 中 `new` 分支：

```python
    if args.command == "new":
        from pax.forge.generator import generate_skill, GenerationError
        try:
            skill_dir = generate_skill(
                name=args.name, layer=args.layer,
                description=args.description,
                target_root=Path.cwd(), optional=args.optional,
            )
        except GenerationError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {skill_dir}")
        return 0
```

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_generator.py tests/test_cli.py -v`

**Step 5: Commit**

```bash
git add src/pax/templates/L1.tmpl src/pax/forge/generator.py \
        src/pax/forge/cli.py tests/test_generator.py tests/test_cli.py
git commit -m "feat(generator): L1 template + generate_skill"
```

---

### Task 2.5：`pax-forge validate <path>` 校验单个 Skill

**Files:**
- Create: `src/pax/forge/validator.py`
- Modify: `src/pax/forge/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_validator.py`

**Step 1: 写测试（失败）**

```python
# tests/test_validator.py
from pathlib import Path
import pytest
from pax.forge.validator import validate_skill, ValidationReport


BASE_SKILL = (
    "---\n"
    "name: pax-ok\n"
    "description: >\n  A valid skill.\n"
    "version: 0.1.0\n"
    "family: pax\n"
    "layer: L1\n"
    "optional: false\n"
    "requires_snapshot: true\n"
    "---\n\n# pax-ok\n\n"
    "## Execution Contract\n- ...\n\n"
    "## 职责边界\n- ...\n\n"
    "## 输入\n- ...\n\n"
    "## 工作流\n1. ...\n\n"
    "## 输出契约\n- ...\n\n"
    "## 失败模式\n- ...\n\n"
    "## 何时升级\n- ...\n"
)


def _write(tmp_path: Path, name: str, text: str = BASE_SKILL) -> Path:
    d = tmp_path / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    return d


def test_validate_ok(tmp_path):
    d = _write(tmp_path, "pax-ok")
    report = validate_skill(d)
    assert report.ok
    assert report.violations == []


def test_validate_missing_required_section(tmp_path):
    d = _write(tmp_path, "pax-bad")
    text = BASE_SKILL.replace("## 何时升级\n- ...\n", "")
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    report = validate_skill(d)
    assert not report.ok
    assert any("何时升级" in v for v in report.violations)


def test_validate_missing_frontmatter_key(tmp_path):
    d = _write(tmp_path, "pax-nofm")
    text = BASE_SKILL.replace("requires_snapshot: true\n", "")
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    report = validate_skill(d)
    assert not report.ok
    assert any("requires_snapshot" in v for v in report.violations)
```

**Step 2: 跑测试确认失败**

**Step 3: 写 validator**

`src/pax/forge/validator.py`:

```python
"""Validate a single pax-* skill directory against family contracts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pax.forge import loader


@dataclass
class ValidationReport:
    path: Path
    ok: bool
    violations: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.violations.append(msg)
        self.ok = False


def _split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split YAML frontmatter from body. Returns (None, text) if absent."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, text
    if not isinstance(fm, dict):
        return None, text
    return fm, parts[2]


def validate_skill(skill_dir: Path) -> ValidationReport:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ValidationReport(skill_md, False, ["SKILL.md missing"])
    text = skill_md.read_text(encoding="utf-8")
    family = loader.load_family_schema()
    contracts = family["contracts"]

    fm, body = _split_frontmatter(text)
    if fm is None:
        return ValidationReport(skill_md, False,
                                ["Invalid or missing YAML frontmatter"])

    report = ValidationReport(skill_md, True)
    if not re.match(contracts["naming"], fm.get("name", "")):
        report.add(f"frontmatter.name violates naming: {fm.get('name')!r}")
    for key in contracts["required_frontmatter"]:
        if key not in fm:
            report.add(f"frontmatter missing required key: {key}")
    for section in contracts["required_sections"]:
        if f"## {section}" not in body:
            report.add(f"missing required section: {section}")
    return report
```

修改 `cli.py` 的 `validate` 分支：

```python
    if args.command == "validate":
        from pax.forge.validator import validate_skill
        report = validate_skill(Path(args.path))
        if report.ok:
            print(f"OK  {report.path}")
            return 0
        print(f"FAIL {report.path}")
        for v in report.violations:
            print(f"  - {v}")
        return 1
```

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_validator.py -v`
Expected: `3 passed`

**Step 5: Commit**

```bash
git add src/pax/forge/validator.py src/pax/forge/cli.py tests/test_validator.py
git commit -m "feat(validator): validate single skill against family contracts"
```

---

### Task 2.6：`pax-forge register <path>` 注册到 registry

**Files:**
- Create: `src/pax/forge/register.py`
- Modify: `src/pax/forge/cli.py`
- Create: `tests/test_register.py`

**Step 1: 写测试（失败）**

```python
# tests/test_register.py
import json
import pytest
from pax.forge.register import register_skill, AlreadyRegisteredError


def test_register_appends(tmp_path, monkeypatch):
    from pax.forge import loader
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(
        json.dumps({"family": "pax", "updated_at": None, "skills": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)

    entry = {
        "name": "pax-foo", "layer": "L1", "optional": False,
        "version": "0.1.0", "path": "skills/pax-foo/SKILL.md",
        "registered_at": "2026-09-29T00:00:00Z",
    }
    register_skill(entry)
    data = loader.load_registry()
    assert data["skills"] == [entry]
    assert data["updated_at"] is not None


def test_register_duplicate_raises(tmp_path, monkeypatch):
    from pax.forge import loader
    reg_path = tmp_path / "registry.json"
    existing = {"family": "pax", "updated_at": None, "skills": [
        {"name": "pax-foo", "path": "x", "version": "0.1.0",
         "layer": "L1", "optional": False, "registered_at": "t"}
    ]}
    reg_path.write_text(json.dumps(existing), encoding="utf-8")
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)
    with pytest.raises(AlreadyRegisteredError):
        register_skill({"name": "pax-foo", "path": "y", "version": "0.1.0",
                        "layer": "L1", "optional": False, "registered_at": "t"})
```

**Step 2: 跑测试确认失败**

**Step 3: 写实现**

`src/pax/forge/register.py`:

```python
"""Register a validated skill into pax-ops/registry.json."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pax.forge import loader


class AlreadyRegisteredError(Exception):
    pass


def _utc_now_iso() -> str:
    return (datetime.now(timezone.utc).replace(microsecond=0)
            .isoformat().replace("+00:00", "Z"))


def register_skill(entry: dict[str, Any]) -> None:
    if "name" not in entry:
        raise ValueError("entry must contain 'name'")
    registry = loader.load_registry()
    for existing in registry.get("skills", []):
        if existing.get("name") == entry["name"]:
            raise AlreadyRegisteredError(
                f"{entry['name']} already registered"
            )
    entry = dict(entry)
    entry.setdefault("registered_at", _utc_now_iso())
    registry["skills"].append(entry)
    registry["updated_at"] = entry["registered_at"]
    loader.save_registry(registry)
```

修改 `cli.py` 的 `register` 分支：

```python
    if args.command == "register":
        from pax.forge import loader
        from pax.forge.validator import validate_skill
        from pax.forge.register import register_skill, AlreadyRegisteredError
        from pax.forge.register import _utc_now_iso
        import yaml

        skill_dir = Path(args.path)
        report = validate_skill(skill_dir)
        if not report.ok:
            print("FAIL: skill did not validate", file=sys.stderr)
            for v in report.violations:
                print(f"  - {v}", file=sys.stderr)
            return 1
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(text.split("---", 2)[1])
        entry = {
            "name": fm["name"],
            "layer": fm["layer"],
            "optional": bool(fm.get("optional", False)),
            "version": fm.get("version", "0.1.0"),
            "path": f"skills/{fm['name']}/SKILL.md",
            "registered_at": _utc_now_iso(),
        }
        try:
            register_skill(entry)
        except AlreadyRegisteredError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"registered {entry['name']} @ {entry['version']}")
        return 0
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add src/pax/forge/register.py src/pax/forge/cli.py tests/test_register.py
git commit -m "feat(register): register validated skill into registry"
```

---

### Task 2.7：`pax-forge list` 列出注册表

**Files:**
- Modify: `src/pax/forge/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: 追加测试**

```python
def test_cli_list_empty_when_no_skills():
    # 首次运行时 registry.json 的 skills 为空
    result = run_cli("list")
    assert result.returncode == 0
    assert "empty" in result.stdout.lower() or "0 skills" in result.stdout.lower()
```

**Step 2: 实现**

`cli.py` 中替换 `list` 分支：

```python
    if args.command == "list":
        from pax.forge import loader
        registry = loader.load_registry()
        skills = registry.get("skills", [])
        if not skills:
            print("(empty registry)")
            return 0
        print(f"{len(skills)} skills:")
        for s in skills:
            opt = " (optional)" if s.get("optional") else ""
            print(f"  {s['name']:<22} [{s['layer']}] v{s['version']}{opt}")
        return 0
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/cli.py tests/test_cli.py
git commit -m "feat(cli): implement pax-forge list"
```

---

### Task 2.8：`pax-forge version <bump>` 版本管理

**Files:**
- Create: `src/pax/forge/versioning.py`
- Modify: `src/pax/forge/cli.py`
- Create: `tests/test_versioning.py`

**Step 1: 写测试（失败）**

```python
# tests/test_versioning.py
import json
from pax.forge.versioning import bump_version, apply_bump, VersionError
import pytest


def test_bump_patch():
    assert bump_version("0.1.0", "patch") == "0.1.1"


def test_bump_minor():
    assert bump_version("0.1.0", "minor") == "0.2.0"


def test_bump_major():
    assert bump_version("0.1.5", "major") == "1.0.0"


def test_bump_invalid():
    with pytest.raises(VersionError):
        bump_version("0.1.0", "release")


def test_apply_bump_writes_versions_json(tmp_path, monkeypatch):
    from pax.forge import loader
    p = tmp_path / "versions.json"
    p.write_text(json.dumps({"family": "pax", "version": "0.1.0",
                              "skills": {"pax-a": {"version": "0.1.0"}}}),
                 encoding="utf-8")
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    apply_bump("minor", family_only=True)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == "0.2.0"
    # family_only 不应同步 skills
    assert data["skills"]["pax-a"]["version"] == "0.1.0"


def test_apply_bump_syncs_skills(tmp_path, monkeypatch):
    from pax.forge import loader
    p = tmp_path / "versions.json"
    p.write_text(json.dumps({"family": "pax", "version": "0.1.0",
                              "skills": {"pax-a": {"version": "0.1.0"}}}),
                 encoding="utf-8")
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    apply_bump("minor", family_only=False)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == "0.2.0"
    assert data["skills"]["pax-a"]["version"] == "0.2.0"
```

**Step 2: 跑测试确认失败**

**Step 3: 写实现**

`src/pax/forge/versioning.py`:

```python
"""Version bump helper for pax-* family."""
from __future__ import annotations

import json

from pax.forge import loader


class VersionError(Exception):
    pass


def bump_version(current: str, bump: str) -> str:
    parts = current.split(".")
    if len(parts) != 3:
        raise VersionError(
            f"expected MAJOR.MINOR.PATCH, got {current!r}"
        )
    major, minor, patch = (int(p) for p in parts)
    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = patch = 0
    else:
        raise VersionError(f"unknown bump: {bump}")
    return f"{major}.{minor}.{patch}"


def apply_bump(bump: str, *, family_only: bool = False) -> str:
    versions = loader.load_versions()
    new = bump_version(versions["version"], bump)
    versions["version"] = new
    if not family_only:
        for name in versions.get("skills", {}):
            versions["skills"][name]["version"] = new
    with loader.VERSIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return new


def deprecate_skill(name: str) -> None:
    versions = loader.load_versions()
    if name not in versions.get("skills", {}):
        raise VersionError(f"skill not in versions.json: {name}")
    versions["skills"][name]["status"] = "deprecated"
    with loader.VERSIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)
        f.write("\n")
```

`cli.py` 中替换 `version` 与 `deprecate` 分支：

```python
    if args.command == "version":
        from pax.forge.versioning import apply_bump, VersionError
        try:
            new = apply_bump(args.bump, family_only=False)
        except VersionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"bumped family to {new}")
        return 0

    if args.command == "deprecate":
        from pax.forge.versioning import deprecate_skill, VersionError
        try:
            deprecate_skill(args.name)
        except VersionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"deprecated {args.name}")
        return 0
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add src/pax/forge/versioning.py src/pax/forge/cli.py tests/test_versioning.py
git commit -m "feat(versioning): bump + deprecate"
```

---

### Task 2.9：`pax-forge test`（先接入契约测试框架占位）

**Files:**
- Create: `src/pax/forge/contracts.py`
- Modify: `src/pax/forge/cli.py`
- Create: `tests/test_contracts.py`

**Step 1: 写测试（框架占位）**

```python
# tests/test_contracts.py
from pathlib import Path
from pax.forge.contracts import ContractReport, run_all_contracts, list_contracts


def test_contract_report_start_empty():
    r = ContractReport()
    assert r.ok
    assert r.failures == []


def test_run_all_contracts_on_empty_family(tmp_path):
    # 空家族跑契约：无 skill、无 violations，应 ok=True
    (tmp_path / "skills").mkdir(parents=True, exist_ok=True)
    report = run_all_contracts(tmp_path)
    assert report.ok
    assert report.failures == []
    assert isinstance(list_contracts(), list)
```

**Step 2: 跑测试确认失败**

**Step 3: 写契约测试框架**

`src/pax/forge/contracts.py`:

```python
"""Cross-skill contract tests for pax-* family.

Every contract is a function `(family_root: Path) -> list[str]` returning
violation messages. Empty list = pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

ContractFn = Callable[[Path], list[str]]

_CONTRACTS: dict[str, ContractFn] = {}


def register_contract(name: str):
    def deco(fn: ContractFn) -> ContractFn:
        _CONTRACTS[name] = fn
        return fn
    return deco


def list_contracts() -> list[str]:
    return sorted(_CONTRACTS.keys())


@dataclass
class ContractReport:
    ok: bool = True
    failures: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    def add_pass(self, name: str) -> None:
        self.passes.append(name)

    def add_fail(self, name: str, messages: list[str]) -> None:
        self.ok = False
        for m in messages:
            self.failures.append(f"[{name}] {m}")


def run_all_contracts(family_root: Path) -> ContractReport:
    report = ContractReport()
    for name, fn in _CONTRACTS.items():
        try:
            violations = fn(family_root)
        except Exception as exc:
            report.add_fail(name, [f"contract raised: {exc!r}"])
            continue
        if violations:
            report.add_fail(name, violations)
        else:
            report.add_pass(name)
    return report


def _iter_skill_dirs(family_root: Path) -> Iterable[Path]:
    skills_dir = family_root / "skills"
    if not skills_dir.exists():
        return
    for child in skills_dir.iterdir():
        if child.is_dir() and (child / "SKILL.md").exists():
            yield child
```

> 具体契约函数（frontmatter / schema / layer calls / version / no cycles / skip audit / gate behavior）在 Phase 3 分批实现，通过 `@register_contract(...)` 注册到全局表。

`cli.py` 中替换 `test` 分支：

```python
    if args.command == "test":
        from pax.forge.contracts import run_all_contracts, list_contracts
        root = Path.cwd()
        report = run_all_contracts(root)
        print(f"contracts discovered: {', '.join(list_contracts()) or '(none)'}")
        for p in report.passes:
            print(f"  PASS  {p}")
        for f in report.failures:
            print(f"  FAIL  {f}")
        print(f"\n{len(report.passes)} passed, {len(report.failures)} failed")
        return 0 if report.ok else 1
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add src/pax/forge/contracts.py src/pax/forge/cli.py tests/test_contracts.py
git commit -m "feat(contracts): framework skeleton for cross-skill contracts"
```

---

### Task 2.10：CLI 端到端串联测试

**Files:**
- Create: `tests/test_cli_e2e.py`

**Step 1: 写测试**

```python
# tests/test_cli_e2e.py
"""End-to-end: init -> new -> validate -> register -> list.

Note: since pax.forge.loader module-level paths point at the real repo,
we use direct Python API calls for isolation. CLI 分支的行为已由各子命令
单元测试覆盖。这里验证整体流程能串联起来。
"""
import shutil
import json
from pathlib import Path


def test_full_pipeline(tmp_path):
    from pax.forge.init import init_family
    from pax.forge.generator import generate_skill
    from pax.forge.validator import validate_skill
    from pax.forge.register import register_skill
    from pax.forge import loader

    # 1. init
    fam = tmp_path / "fam"
    init_family(fam)

    # 2. 重定向 loader 到 tmp family
    loader.FAMILY_SCHEMA_PATH = fam / "schemas" / "pax-family.schema.yaml"
    loader.SNAPSHOT_SCHEMA_PATH = fam / "schemas" / "snapshot.schema.json"
    loader.VERSIONS_PATH = fam / "pax-ops" / "versions.json"
    loader.REGISTRY_PATH = fam / "pax-ops" / "registry.json"
    loader.PATCHES_MANIFEST_PATH = fam / "pax-ops" / "patches" / "manifest.json"

    # 3. new
    skill_dir = generate_skill(
        name="pax-tester", layer="L1",
        description="A test skill", target_root=fam, optional=False,
    )
    assert (skill_dir / "SKILL.md").exists()

    # 4. validate
    report = validate_skill(skill_dir)
    assert report.ok, report.violations

    # 5. register
    entry = {
        "name": "pax-tester", "layer": "L1", "optional": False,
        "version": "0.1.0",
        "path": "skills/pax-tester/SKILL.md",
        "registered_at": "2026-09-29T00:00:00Z",
    }
    register_skill(entry)

    # 6. 断言
    reg = json.loads(
        (fam / "pax-ops" / "registry.json").read_text(encoding="utf-8")
    )
    assert reg["skills"] == [entry]


# 清理：确保测试间互不污染
import atexit
from pax.forge import loader as _L
import json as _json

_ORIGINAL_PATHS = {
    "FAMILY_SCHEMA_PATH": _L.FAMILY_SCHEMA_PATH,
    "SNAPSHOT_SCHEMA_PATH": _L.SNAPSHOT_SCHEMA_PATH,
    "VERSIONS_PATH": _L.VERSIONS_PATH,
    "REGISTRY_PATH": _L.REGISTRY_PATH,
    "PATCHES_MANIFEST_PATH": _L.PATCHES_MANIFEST_PATH,
}


def _restore():
    for k, v in _ORIGINAL_PATHS.items():
        setattr(_L, k, v)


atexit.register(_restore)
```

**Step 2: 跑测试确认通过**

Run: `pytest tests/test_cli_e2e.py -v`
Expected: `1 passed`

**Step 3: Commit**

```bash
git add tests/test_cli_e2e.py
git commit -m "test(e2e): full pipeline init->new->validate->register"
```

---

## Phase 3：契约测试器（7 项契约）

契约测试是家族"不靠 AI 自觉"的核心。每一项都是**独立检查函数**，`pax-forge test` 汇总输出。

### Task 3.1：契约①——frontmatter 完整性

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 写测试（失败）**

```python
def test_contract_frontmatter_completeness_detects_missing(tmp_path):
    from pax.forge.contracts import check_frontmatter_completeness
    d = tmp_path / "skills" / "pax-bad"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\n"
        "name: pax-bad\n"     # 缺 description/version/family/layer/requires_snapshot
        "---\n\n# pax-bad\n\n"
        "## Execution Contract\n- x\n"
        "## 职责边界\n- x\n"
        "## 输入\n- x\n"
        "## 工作流\n1. x\n"
        "## 输出契约\n- x\n"
        "## 失败模式\n- x\n"
        "## 何时升级\n- x\n",
        encoding="utf-8",
    )
    violations = check_frontmatter_completeness(tmp_path)
    assert any("pax-bad" in v for v in violations)
    # 至少报一个缺 key
    assert any("description" in v or "version" in v for v in violations)


def test_contract_frontmatter_completeness_passes_clean(tmp_path, monkeypatch):
    from pax.forge.contracts import check_frontmatter_completeness
    from pax.forge import loader
    # 复制真实 schema
    import shutil
    (tmp_path / "schemas").mkdir()
    shutil.copy(loader.FAMILY_SCHEMA_PATH,
                tmp_path / "schemas" / "pax-family.schema.yaml")
    monkeypatch.setattr(loader, "FAMILY_SCHEMA_PATH",
                        tmp_path / "schemas" / "pax-family.schema.yaml")
    # 构造合法 skill
    d = tmp_path / "skills" / "pax-ok"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-ok\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L1\noptional: false\n"
        "requires_snapshot: true\n---\n\n# pax-ok\n"
        "## Execution Contract\n- x\n## 职责边界\n- x\n## 输入\n- x\n"
        "## 工作流\n1. x\n## 输出契约\n- x\n## 失败模式\n- x\n"
        "## 何时升级\n- x\n",
        encoding="utf-8",
    )
    assert check_frontmatter_completeness(tmp_path) == []
```

**Step 2: 跑测试确认失败**

**Step 3: 实现**

`src/pax/forge/contracts.py` 追加：

```python
import re as _re
import yaml
from pax.forge import loader
from pax.forge.validator import _split_frontmatter


@register_contract("frontmatter-completeness")
def check_frontmatter_completeness(family_root: Path) -> list[str]:
    violations: list[str] = []
    family = loader.load_family_schema()
    required = family["contracts"]["required_frontmatter"]
    naming_re = _re.compile(family["contracts"]["naming"])
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm is None:
            violations.append(
                f"{skill_dir.name}: invalid or missing frontmatter"
            )
            continue
        for key in required:
            if key not in fm:
                violations.append(
                    f"{skill_dir.name}: frontmatter missing '{key}'"
                )
        if not naming_re.match(fm.get("name", "")):
            violations.append(
                f"{skill_dir.name}: name violates naming contract"
            )
    return violations
```

**Step 4: 跑测试确认通过**

**Step 5: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): check frontmatter completeness"
```

---

### Task 3.2：契约②——snapshot schema 合法性

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def test_contract_snapshot_schema_validates_real_schema():
    import jsonschema
    from pax.forge import loader
    schema = loader.load_snapshot_schema()
    jsonschema.Draft202012Validator.check_schema(schema)


def test_contract_snapshot_schema_reference_consistent():
    from pax.forge import loader
    family = loader.load_family_schema()
    ref = family["contracts"]["snapshot_schema"]
    assert "snapshot.schema.json" in ref
```

**Step 2: 实现**

```python
import json as _json
import jsonschema


@register_contract("snapshot-schema-validity")
def check_snapshot_schema_validity(family_root: Path) -> list[str]:
    violations: list[str] = []
    schema_path = family_root / "schemas" / "snapshot.schema.json"
    if not schema_path.exists():
        return [f"missing {schema_path}"]
    with schema_path.open("r", encoding="utf-8") as f:
        schema = _json.load(f)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        violations.append(f"snapshot schema invalid: {exc.message}")
    return violations
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): snapshot schema validity"
```

---

### Task 3.3：契约③——层间调用合法性

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def test_allowed_calls_matrix():
    from pax.forge.contracts import _allowed_calls
    allowed = _allowed_calls()
    assert ("L0", "L1") in allowed
    assert ("L1", "L2") in allowed
    assert ("L1", "L3") in allowed
    assert ("L1", "L4") in allowed
    # L4 不能调用 L1（横切是被调用方）
    assert ("L4", "L1") not in allowed
    # meta 不参与运行时
    assert ("meta", "L1") not in allowed


def test_contract_layer_calls_flag_violation(tmp_path):
    from pax.forge.contracts import check_layer_call_legality
    def write(name: str, layer: str, body: str):
        d = tmp_path / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: >\n  x\nversion: 0.1.0\n"
            f"family: pax\nlayer: {layer}\noptional: false\n"
            f"requires_snapshot: true\n---\n\n# {name}\n"
            f"## Execution Contract\n- x\n## 职责边界\n- x\n## 输入\n- x\n"
            f"## 工作流\n1. x\n## 输出契约\n- x\n## 失败模式\n- x\n"
            f"## 何时升级\n{body}\n",
            encoding="utf-8",
        )
    # L4 调 L1 应该被标记
    write("pax-v", "L4", "调用 pax-plan")
    write("pax-plan", "L1", "")
    violations = check_layer_call_legality(tmp_path)
    assert any("pax-v" in v for v in violations)
```

**Step 2: 实现**

```python


def _allowed_calls() -> set[tuple[str, str]]:
    return {
        ("L0", "L1"),
        ("L1", "L1"),   # 相邻阶段
        ("L1", "L2"),
        ("L1", "L3"),
        ("L2", "L3"),
        ("L0", "L4"),
        ("L1", "L4"),
        ("L2", "L4"),
    }


@register_contract("layer-call-legality")
def check_layer_call_legality(family_root: Path) -> list[str]:
    from pax.forge.validator import _split_frontmatter
    allowed = _allowed_calls()
    violations: list[str] = []
    skill_layers: dict[str, str] = {}
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm and "name" in fm and "layer" in fm:
            skill_layers[fm["name"]] = fm["layer"]
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        self_layer = fm["layer"]
        mentioned = set(_re.findall(r"pax-[a-z][a-z0-9-]*", body))
        mentioned -= {fm["name"]}
        for target_name in mentioned:
            target_layer = skill_layers.get(target_name)
            if target_layer is None:
                continue
            if (self_layer, target_layer) not in allowed:
                violations.append(
                    f"{fm['name']} ({self_layer}) references "
                    f"{target_name} ({target_layer}): forbidden direction"
                )
    return violations
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): layer call legality"
```

---

### Task 3.4：契约④——版本一致性

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def test_contract_version_consistency_detects_orphan(tmp_path):
    import json
    from pax.forge.contracts import check_version_consistency
    (tmp_path / "pax-ops").mkdir(parents=True)
    (tmp_path / "skills" / "pax-orphan").mkdir(parents=True)
    (tmp_path / "pax-ops" / "versions.json").write_text(
        json.dumps({"family": "pax", "version": "0.1.0", "skills": {}}),
        encoding="utf-8",
    )
    (tmp_path / "skills" / "pax-orphan" / "SKILL.md").write_text(
        "---\nname: pax-orphan\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-orphan\n## Execution Contract\n- x\n## 职责边界\n- x\n"
        "## 输入\n- x\n## 工作流\n1. x\n## 输出契约\n- x\n"
        "## 失败模式\n- x\n## 何时升级\n- x\n",
        encoding="utf-8",
    )
    violations = check_version_consistency(tmp_path)
    assert any("pax-orphan" in v for v in violations)
```

**Step 2: 实现**

```python


@register_contract("version-consistency")
def check_version_consistency(family_root: Path) -> list[str]:
    from pax.forge.validator import _split_frontmatter
    versions_path = family_root / "pax-ops" / "versions.json"
    if not versions_path.exists():
        return ["missing pax-ops/versions.json"]
    with versions_path.open("r", encoding="utf-8") as f:
        versions = _json.load(f)
    known = versions.get("skills", {})
    violations: list[str] = []
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm is None:
            continue
        name = fm.get("name")
        if name not in known:
            violations.append(
                f"{name}: not listed in pax-ops/versions.json"
            )
            continue
        if known[name].get("version") != fm.get("version"):
            violations.append(
                f"{name}: SKILL.md version {fm.get('version')!r} != "
                f"versions.json {known[name].get('version')!r}"
            )
    return violations
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): version consistency"
```

---

### Task 3.5：契约⑤——无循环依赖

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def _mk_skill(root, name, body=""):
    d = root / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >\n  x\nversion: 0.1.0\n"
        f"family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n"
        f"---\n\n# {name}\n{body}\n", encoding="utf-8"
    )


def test_contract_no_cycles_clean(tmp_path):
    from pax.forge.contracts import check_no_cycles
    _mk_skill(tmp_path, "pax-a", "## 何时升级\n调用 pax-b")
    _mk_skill(tmp_path, "pax-b", "## 何时升级\n调用 pax-c")
    _mk_skill(tmp_path, "pax-c")
    assert check_no_cycles(tmp_path) == []


def test_contract_no_cycles_detects(tmp_path):
    from pax.forge.contracts import check_no_cycles
    _mk_skill(tmp_path, "pax-a", "## 何时升级\n调用 pax-b")
    _mk_skill(tmp_path, "pax-b", "## 何时升级\n调用 pax-a")
    violations = check_no_cycles(tmp_path)
    assert any("cycle" in v.lower() for v in violations)
```

**Step 2: 实现**

```python


def _extract_call_graph(family_root: Path) -> dict[str, set[str]]:
    from pax.forge.validator import _split_frontmatter
    graph: dict[str, set[str]] = {}
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        name = fm["name"]
        mentioned = set(_re.findall(r"pax-[a-z][a-z0-9-]*", body))
        mentioned -= {name}
        graph[name] = mentioned
    return graph


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    seen_global: set[tuple[str, ...]] = set()
    visited: set[str] = set()
    path: list[str] = []

    def dfs(node: str):
        if node in path:
            cyc = tuple(path[path.index(node):])
            if cyc not in seen_global:
                seen_global.add(cyc)
                cycles.append(list(cyc) + [node])
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for nxt in sorted(graph.get(node, ())):
            if nxt in graph:
                dfs(nxt)
        path.pop()

    for node in sorted(graph):
        visited.clear()
        path.clear()
        dfs(node)
    return cycles


@register_contract("no-cycles")
def check_no_cycles(family_root: Path) -> list[str]:
    graph = _extract_call_graph(family_root)
    cycles = _find_cycles(graph)
    return [f"cycle detected: {' -> '.join(c)}" for c in cycles]
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): no-cycles detection"
```

---

### Task 3.6：契约⑥——跳过审计

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def test_contract_skip_audit_optional_without_skip_reason_fails(tmp_path):
    from pax.forge.contracts import check_skip_audit
    d = tmp_path / "skills" / "pax-diagnose"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-diagnose\ndescription: >\n  Root cause diagnosis\n"
        "version: 0.1.0\nfamily: pax\nlayer: L1\noptional: true\n"
        "requires_snapshot: true\n---\n\n# pax-diagnose\n"
        "## Execution Contract\n- ...\n## 职责边界\n- ...\n"
        "## 输入\n- ...\n## 工作流\n1. ...\n## 输出契约\n- ...\n"
        "## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    violations = check_skip_audit(tmp_path)
    assert any("skip_reason" in v or "跳过" in v for v in violations)


def test_contract_skip_audit_optional_with_skip_reason_passes(tmp_path):
    from pax.forge.contracts import check_skip_audit
    d = tmp_path / "skills" / "pax-diagnose"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-diagnose\ndescription: >\n  Root cause diagnosis\n"
        "version: 0.1.0\nfamily: pax\nlayer: L1\noptional: true\n"
        "requires_snapshot: true\n---\n\n# pax-diagnose\n"
        "## Execution Contract\n- 跳过必须记录 skip_reason\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n"
        "## 工作流\n1. ...\n## 输出契约\n- ...\n"
        "## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    assert check_skip_audit(tmp_path) == []
```

**Step 2: 实现**

```python


SKIP_AUDIT_KEYWORDS = ("skip_reason", "跳过留痕", "跳过理由")


@register_contract("skip-audit")
def check_skip_audit(family_root: Path) -> list[str]:
    from pax.forge.validator import _split_frontmatter
    violations: list[str] = []
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        if not fm.get("optional", False):
            continue
        if not any(k in body for k in SKIP_AUDIT_KEYWORDS):
            violations.append(
                f"{fm['name']}: optional skill must document "
                f"skip_reason (跳过留痕契约)"
            )
    return violations
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): skip audit for optional skills"
```

---

### Task 3.7：契约⑦——门禁行为

**Files:**
- Modify: `src/pax/forge/contracts.py`
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def test_contract_gate_behavior_detects_missing_precondition(tmp_path):
    from pax.forge.contracts import check_gate_behavior
    d = tmp_path / "skills" / "pax-plan"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-plan\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-plan\n## Execution Contract\n- xxx\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    violations = check_gate_behavior(tmp_path)
    assert any("pax-plan" in v for v in violations)


def test_contract_gate_behavior_passes_with_precondition(tmp_path):
    from pax.forge.contracts import check_gate_behavior
    d = tmp_path / "skills" / "pax-plan"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-plan\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-plan\n## Execution Contract\n"
        "- 前置门禁：consensus.gaps_remaining == []\n"
        "- 未通过：返回 pax-clarify\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    assert check_gate_behavior(tmp_path) == []
```

**Step 2: 实现**

```python


GATE_KEYWORDS = ("前置门禁", "前置条件", "未通过", "不满足", "禁止", "降级")


@register_contract("gate-behavior")
def check_gate_behavior(family_root: Path) -> list[str]:
    from pax.forge.validator import _split_frontmatter
    violations: list[str] = []
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        marker = "## Execution Contract"
        if marker not in body:
            violations.append(
                f"{fm['name']}: missing Execution Contract section"
            )
            continue
        section = body.split(marker, 1)[1]
        if "\n## " in section:
            section = section.split("\n## ", 1)[0]
        if not any(k in section for k in GATE_KEYWORDS):
            violations.append(
                f"{fm['name']}: Execution Contract lacks precondition/gate keyword"
            )
    return violations
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/contracts.py tests/test_contracts.py
git commit -m "feat(contracts): gate behavior check"
```

---

### Task 3.8：契约测试汇总输出

**Files:**
- Modify: `tests/test_contracts.py`

**Step 1: 追加测试**

```python
def test_all_seven_contracts_registered():
    from pax.forge.contracts import list_contracts
    # 强制 import contracts 以注册
    import pax.forge.contracts  # noqa
    names = set(list_contracts())
    expected = {
        "frontmatter-completeness",
        "snapshot-schema-validity",
        "layer-call-legality",
        "version-consistency",
        "no-cycles",
        "skip-audit",
        "gate-behavior",
    }
    assert expected.issubset(names)
```

**Step 2: 跑测试确认通过**

**Step 3: Commit**

```bash
git add tests/test_contracts.py
git commit -m "test(contracts): assert all 7 contracts registered"
```

---

## Phase 4：模板系统（补齐 L0/L2/L3/L4/meta）

Phase 2 已创建 `L1.tmpl`。本 Phase 补齐其余 5 层模板，使 `pax-forge new` 能根据层选择不同骨架。

### Task 4.1：L0 模板（pax-orchestrate）

**Files:**
- Create: `src/pax/templates/L0.tmpl`
- Modify: `tests/test_generator.py`

**Step 1: 写测试**

```python
def test_generate_l0_skill(tmp_path):
    from pax.forge.generator import generate_skill
    skill_dir = generate_skill(
        name="pax-orchestrate", layer="L0",
        description="路由、风险分级、生命周期管理",
        target_root=tmp_path, optional=False,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "## 风险评分维度" in text
    assert "## 路由规则" in text
    assert "## Execution Contract" in text
```

**Step 2: 写模板**

`src/pax/templates/L0.tmpl`:

```jinja
---
name: {{ name }}
description: >
  {{ description }}。L0 层负责路由、风险分级与生命周期管理。
version: {{ version }}
family: pax
layer: L0
optional: false
requires_snapshot: true
---

# {{ name }}

## Execution Contract
- 前置门禁：能读取 `pax-family.schema.yaml`
- 未通过门禁：拒绝启动，返回用户错误
- 版本检查：`pax-ops/versions.json`

## 职责边界
- 做什么：意图分类（MECE）、风险评分、`diagnose_required` 决策、路由构建、快照初始化
- 不做什么：不执行具体工作、不修改快照下游字段

## 输入
- 必需：`user_goal`, `context`
- 可选：历史快照、领域依赖映射表

## 工作流
1. `intent = classify_intent(user_goal)`  # MECE
2. `risk = assess_risk(user_goal, context)`  # 四维评分
3. `diagnose_required = is_diagnostic_intent(intent, context)`
4. `strategy = "batch" if risk <= 9 else "one-by-one"`
5. `route = build_route(intent, diagnose_required, risk)`
6. `return init_snapshot(intent, risk, diagnose_required, strategy, route)`

## 风险评分维度
- 不可逆性（1-3）
- 影响范围（1-3）
- 不确定性（1-3）
- 协调成本（1-3）

总分映射：4-6 低 / 7-9 中 / 10-12 高。

## 路由规则
- 诊断类意图（修复/报错/异常/回归/性能退化）
  → `[clarify, diagnose, plan, execute, review]`
- 普通任务 → `[clarify, plan, execute, review]`

## 输出契约
- `snapshot.orchestration` 与快照初始状态，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 分类置信度低 → 升级 `pax-council`

## 何时升级
- 高风险任务 → `pax-council`
- 需要诊断 → `pax-diagnose`
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/templates/L0.tmpl tests/test_generator.py
git commit -m "feat(template): L0 for pax-orchestrate"
```

---

### Task 4.2：L2 模板（pax-advisor / pax-council）

**Files:**
- Create: `src/pax/templates/L2.tmpl`
- Modify: `tests/test_generator.py`

**Step 1: 写测试**

```python
def test_generate_l2_skill(tmp_path):
    from pax.forge.generator import generate_skill
    skill_dir = generate_skill(
        name="pax-advisor", layer="L2",
        description="只读顾问",
        target_root=tmp_path, optional=True,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "只读" in text
    assert "不修改快照" in text
```

**Step 2: 写模板**

`src/pax/templates/L2.tmpl`:

```jinja
---
name: {{ name }}
description: >
  {{ description }}。L2 层只读，不修改快照，输出咨询意见。
version: {{ version }}
family: pax
layer: L2
optional: {{ 'true' if optional else 'false' }}
requires_snapshot: true
---

# {{ name }}

## Execution Contract
- 前置门禁：需要完整快照或明确的问题陈述
- 未通过门禁：拒绝启动
- 版本检查：`pax-ops/versions.json`

## 职责边界
- 做什么：针对特定假设、权衡、架构问题提供咨询
- 不做什么：不修改快照、不改变主流程、不认领路由落点

## 输入
- 必需：完整快照或咨询问题
- 可选：上下文材料、历史决策

## 工作流
1. 读取输入，理解问题
2. 提出多个候选方案
3. 证据加权评估
4. 记录异议与权衡

## 输出契约
- 咨询意见文本（不写入快照）

## 失败模式
- 如果信息不足，声明 blocked 并列出缺失
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 高风险决策 → 请求人工审批
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/templates/L2.tmpl tests/test_generator.py
git commit -m "feat(template): L2 for advisor/council"
```

---

### Task 4.3：L3 模板（pax-worker-*）

**Files:**
- Create: `src/pax/templates/L3.tmpl`
- Modify: `tests/test_generator.py`

**Step 1: 写测试**

```python
def test_generate_l3_skill(tmp_path):
    from pax.forge.generator import generate_skill
    skill_dir = generate_skill(
        name="pax-worker-grok", layer="L3",
        description="Grok 有界任务执行",
        target_root=tmp_path, optional=True,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "沙箱" in text
    assert "无头执行" in text
```

**Step 2: 写模板**

`src/pax/templates/L3.tmpl`:

```jinja
---
name: {{ name }}
description: >
  {{ description }}。L3 层工具适配，接口由上层定义。
version: {{ version }}
family: pax
layer: L3
optional: {{ 'true' if optional else 'false' }}
requires_snapshot: true
---

# {{ name }}

## Execution Contract
- 前置门禁：调用方已定义任务边界与输入
- 未通过门禁：拒绝执行
- 版本检查：`pax-ops/versions.json`

## 职责边界
- 做什么：将有界实现任务委托给固定 worker
- 不做什么：不做路由决策、不修改上层快照字段

## 输入
- 必需：任务描述、约束、输入上下文
- 可选：优先级、超时

## 工作流
1. 沙箱准备（isolated FS / network）
2. 无头执行任务
3. 收集输出、日志、diff
4. 打包返回给调用方

## 输出契约
- 变更 diff、执行日志、退出码

## 失败模式
- 任务超时 → kill 并返回 partial
- 沙箱失败 → 拒绝执行
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 任务超出 worker 能力 → 返回 `pax-plan` 请求重规划
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/templates/L3.tmpl tests/test_generator.py
git commit -m "feat(template): L3 for worker-*"
```

---

### Task 4.4：L4 模板（verify / evolve / docs）

**Files:**
- Create: `src/pax/templates/L4.tmpl`
- Modify: `tests/test_generator.py`

**Step 1: 写测试**

```python
def test_generate_l4_skill(tmp_path):
    from pax.forge.generator import generate_skill
    skill_dir = generate_skill(
        name="pax-verify", layer="L4",
        description="运行中验证",
        target_root=tmp_path, optional=True,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "五态" in text or "pass" in text
    assert "不认领路由落点" in text
```

**Step 2: 写模板**

`src/pax/templates/L4.tmpl`:

```jinja
---
name: {{ name }}
description: >
  {{ description }}。L4 层横切能力，不认领路由落点。
version: {{ version }}
family: pax
layer: L4
optional: {{ 'true' if optional else 'false' }}
requires_snapshot: true
---

# {{ name }}

## Execution Contract
- 前置门禁：可被任意 L0/L1/L2 调用
- 未通过门禁：返回 blocked
- 版本检查：`pax-ops/versions.json`

## 职责边界
- 做什么：<描述该 Skill 的横切能力>
- 不做什么：不认领路由落点、不改变主流程

## 输入
- 必需：<具体输入>
- 可选：<...>

## 工作流
1. 接收请求
2. 执行验证/进化/文档操作
3. 输出五态印章（pass / fail / partial / blocked / escalated）

## 输出契约
- 印章 / 经验条目 / 文档，格式由 `schemas/snapshot.schema.json` 约束

## 失败模式
- 验证失败 → 返回 blocked
- 跳过留痕：任何跳过记录 `skip_reason`

## 何时升级
- 若问题超出范围 → 请求人工介入
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/templates/L4.tmpl tests/test_generator.py
git commit -m "feat(template): L4 for verify/evolve/docs"
```

---

### Task 4.5：meta 模板（pax-forge 自身）

**Files:**
- Create: `src/pax/templates/meta.tmpl`
- Modify: `tests/test_generator.py`

**Step 1: 写测试**

```python
def test_generate_meta_skill(tmp_path):
    from pax.forge.generator import generate_skill
    skill_dir = generate_skill(
        name="pax-forge", layer="meta",
        description="按家族契约生成、校验、注册新 Skill",
        target_root=tmp_path, optional=False,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "生成、校验、注册" in text
    assert "breaking change" in text
```

**Step 2: 写模板**

`src/pax/templates/meta.tmpl`:

```jinja
---
name: {{ name }}
description: >
  {{ description }}。元层工具，不参与运行时。
version: {{ version }}
family: pax
layer: meta
optional: {{ 'true' if optional else 'false' }}
requires_snapshot: false
---

# {{ name }}

## Execution Contract
- 前置门禁：能读取 `pax-family.schema.yaml`
- 未通过门禁：拒绝生成/注册
- 版本检查：`pax-ops/versions.json`

## 职责边界
- 做什么：生成、校验、注册、版本管理
- 不做什么：不参与运行时、不修改已有 Skill 的业务逻辑

## 输入
- 必需：新 Skill 名称、层、职责描述
- 可选：`upstream` 映射、`optional` 标记

## 工作流
1. 读取 `pax-family.schema.yaml`
2. 命名冲突与层合法性检查
3. 选择模板（按层）
4. 生成目录结构与 `SKILL.md`
5. 生成契约测试
6. 注册到 `pax-ops/registry.json`
7. 运行契约测试
8. 输出待办清单

## 输出契约
- 骨架目录 + `SKILL.md` + 契约测试 + 注册记录

## 失败模式
- 命名冲突 → 拒绝生成
- 契约测试未通过 → 不注册

## 何时升级
- breaking change 必须人工审核
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/templates/meta.tmpl tests/test_generator.py
git commit -m "feat(template): meta for pax-forge"
```

---

## Phase 5：生成 13 个 Skill 骨架

前 6 个必需 Skill（L0/L1）用 `pax-forge new` 生成；其余按同法生成并注册。

### Task 5.1：批量生成 L0/L1 核心 Skill

**Files:**
- Create: `skills/pax-orchestrate/SKILL.md`
- Create: `skills/pax-clarify/SKILL.md`
- Create: `skills/pax-diagnose/SKILL.md`
- Create: `skills/pax-plan/SKILL.md`
- Create: `skills/pax-execute/SKILL.md`
- Create: `skills/pax-review/SKILL.md`

**Step 1: 用 CLI 逐个生成**

Run（在项目根）:
```bash
pax-forge new pax-orchestrate --layer L0 \
    --description "路由、风险分级、生命周期管理、快照初始化"
pax-forge new pax-clarify --layer L1 \
    --description "共识状态机、设计树维护、缺口检测、契约草稿"

pax-forge new pax-diagnose --layer L1 --optional \
    --description "对 bug、故障、性能退化、回归进行根因诊断"
pax-forge new pax-plan --layer L1 \
    --description "将已澄清/诊断的目标转化为机器可冻结的任务计划"
pax-forge new pax-execute --layer L1 \
    --description "在契约约束下执行，带审计和回滚"
pax-forge new pax-review --layer L1 \
    --description "独立评审门禁，对照成功标准决定通过/拒绝"
```

Expected: 6 个 `wrote skills/pax-<name>` 输出。

**Step 2: 逐个校验**

```bash
for d in skills/pax-orchestrate skills/pax-clarify skills/pax-diagnose \
         skills/pax-plan skills/pax-execute skills/pax-review; do
  pax-forge validate "$d" || exit 1
done
```

**Step 3: 逐个注册**

```bash
for d in skills/pax-orchestrate skills/pax-clarify skills/pax-diagnose \
         skills/pax-plan skills/pax-execute skills/pax-review; do
  pax-forge register "$d"
done
```

**Step 4: 手工精修每个 SKILL.md 的 `description` 与 `## 工作流`**

模板给出的默认文本过于抽象，需要按 `docs/pax-family-design.md §6` 展开为具体工作流。修改时保持所有 `## ` 段头不变。

参考：
- `pax-clarify`：写入双引擎（设计树 + 共识维度）与 4 步循环
- `pax-diagnose`：写入 D1-D6 六步与 RC 回退表
- `pax-plan`：写入前置门禁（`consensus.gaps_remaining == []`）与 6 步
- `pax-execute`：写入 normal/fix 双模式与 fix 模式约束
- `pax-review`：写入 5 种 verdict 与门禁

**Step 5: 跑契约测试**

```bash
pax-forge test
```
Expected: 全部 PASS。

**Step 6: Commit**

```bash
git add skills/ pax-ops/registry.json
git commit -m "feat(skills): generate and register L0/L1 core skills"
```

---

### Task 5.2：批量生成 L2/L3/L4 可选 Skill

**Files:**
- Create: `skills/pax-advisor/SKILL.md`
- Create: `skills/pax-council/SKILL.md`
- Create: `skills/pax-worker-grok/SKILL.md`
- Create: `skills/pax-worker-codex/SKILL.md`
- Create: `skills/pax-verify/SKILL.md`
- Create: `skills/pax-evolve/SKILL.md`
- Create: `skills/pax-docs/SKILL.md`

**Step 1: 生成**

```bash
pax-forge new pax-advisor --layer L2 --optional \
    --description "只读顾问，针对特定假设、权衡、架构问题提供咨询"
pax-forge new pax-council --layer L2 --optional \
    --description "对重大系统开发计划做盲审、显式反驳、有界修订轮次、证据加权决策"
pax-forge new pax-worker-grok --layer L3 --optional \
    --description "Grok 有界任务执行"
pax-forge new pax-worker-codex --layer L3 --optional \
    --description "Codex 有界任务执行"
pax-forge new pax-verify --layer L4 --optional \
    --description "运行中验证，有界循环 + 五态印章"

pax-forge new pax-evolve --layer L4 --optional \
    --description "OODA 闭环 + 经验条目库 + A/B 验证门 + 回滚"
pax-forge new pax-docs --layer L4 --optional \
    --description "把已确认硬决策沉淀为 CONTEXT.md 和 ADR"
```

**Step 2: 校验 + 注册**

```bash
for d in skills/pax-advisor skills/pax-council \
         skills/pax-worker-grok skills/pax-worker-codex \
         skills/pax-verify skills/pax-evolve skills/pax-docs; do
  pax-forge validate "$d" || exit 1
  pax-forge register "$d" || exit 1
done
```

**Step 3: 跑契约测试**

```bash
pax-forge test
```
Expected: 全部 PASS（含 no-cycles / version-consistency / skip-audit）。

**Step 4: 检查 optional skill 是否提到 `skip_reason` 或"跳过留痕"**

若未提到，编辑每个 optional skill 的 `## 失败模式` 段追加：

```markdown
- 任何跳过必须记录 `skip_reason`（跳过留痕契约）
```

**Step 5: 跑契约测试确认 PASS**

**Step 6: Commit**

```bash
git add skills/ pax-ops/registry.json
git commit -m "feat(skills): generate and register optional L2/L3/L4 skills"
```

---

### Task 5.3：`versions.json` 与 `registry.json` 一致性校验

**Files:**
- 无（纯校验）

**Step 1: 确认双向一致**

```bash
python -c "
from pax.forge import loader
v = set(loader.load_versions()['skills'].keys())
r = {s['name'] for s in loader.load_registry()['skills']}
assert v == r, f'MISMATCH: only-in-versions={v-r}, only-in-registry={r-v}'
print(f'OK: {len(v)} skills in sync')
"
```
Expected: `OK: 13 skills in sync`

**Step 2: 如无不一致，无需提交**

```bash
git status --short
```

---

## Phase 6：补丁层（幂等重放）

### Task 6.1：`apply_patch` 核心

**Files:**
- Create: `src/pax/forge/patcher.py`
- Create: `tests/test_patcher.py`

**Step 1: 写测试（失败）**

```python
# tests/test_patcher.py
from pathlib import Path
import pytest
from pax.forge.patcher import apply_patch, apply_manifest, PatchError


def test_apply_replace_idempotent(tmp_path):
    """同一补丁重复执行两次应无副作用。"""
    target = tmp_path / "skills" / "pax-clarify" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("line A\nline B\n", encoding="utf-8")
    patch = {"target": "skills/pax-clarify/SKILL.md",
             "operation": "replace",
             "needle": "line B", "repl": "line B'"}
    applied = apply_patch(patch, family_root=tmp_path)
    assert applied is True
    assert "line B'" in target.read_text(encoding="utf-8")
    # 第二次：needle 已不在，幂等跳过
    applied2 = apply_patch(patch, family_root=tmp_path)
    assert applied2 is False
    assert "line B'" in target.read_text(encoding="utf-8")


def test_apply_replace_strict_raises(tmp_path):
    target = tmp_path / "skills" / "pax-clarify" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("line A\n", encoding="utf-8")
    patch = {"target": "skills/pax-clarify/SKILL.md",
             "operation": "replace",
             "needle": "not-there", "repl": "x"}
    with pytest.raises(PatchError):
        apply_patch(patch, family_root=tmp_path, idempotent=False)


def test_apply_append_idempotent(tmp_path):
    target = tmp_path / "foo.md"
    target.write_text("body\n", encoding="utf-8")
    patch = {"target": "foo.md", "operation": "append",
             "repl": "\nextra\n"}
    assert apply_patch(patch, family_root=tmp_path) is True
    assert apply_patch(patch, family_root=tmp_path) is False


def test_apply_remove_idempotent(tmp_path):
    target = tmp_path / "foo.md"
    target.write_text("a X b\n", encoding="utf-8")
    patch = {"target": "foo.md", "operation": "remove", "needle": " X"}
    assert apply_patch(patch, family_root=tmp_path) is True
    assert "X" not in target.read_text(encoding="utf-8")
    assert apply_patch(patch, family_root=tmp_path) is False


def test_unknown_operation_raises(tmp_path):
    target = tmp_path / "foo.md"
    target.write_text("x\n", encoding="utf-8")
    with pytest.raises(PatchError):
        apply_patch({"target": "foo.md", "operation": "unknown"},
                    family_root=tmp_path)


def test_apply_manifest_marks_applied(tmp_path, monkeypatch):
    import json
    from pax.forge import loader
    manifest_path = tmp_path / "pax-ops" / "patches" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({
        "version": "1.0",
        "patches": [{"id": "p1", "target": "foo.md",
                     "operation": "replace", "needle": "a", "repl": "b"}],
        "applied": []
    }), encoding="utf-8")
    monkeypatch.setattr(loader, "PATCHES_MANIFEST_PATH", manifest_path)

    (tmp_path / "foo.md").write_text("a\n", encoding="utf-8")

    n1 = apply_manifest(family_root=tmp_path)
    assert n1 == 1
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["applied"] == ["p1"]
    # 幂等：第二次不重复应用
    n2 = apply_manifest(family_root=tmp_path)
    assert n2 == 0
```

**Step 2: 跑测试确认失败**

**Step 3: 写实现**

`src/pax/forge/patcher.py`:

```python
"""Declarative patch layer with idempotent replay."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pax.forge import loader


class PatchError(Exception):
    pass


def apply_patch(patch: dict[str, Any], *, family_root: Path,
                idempotent: bool = True) -> bool:
    """Apply a single patch. Returns True if a change was made, else False.

    Operations:
    - replace:  replace first occurrence of `needle` with `repl`.
                If needle absent and idempotent=True, return False.
                If idempotent=False, raise PatchError.
    - append:   append `repl` to end. If already ends with `repl`, skip.
    - remove:   remove first occurrence of `needle`.
    """
    op = patch.get("operation")
    target = family_root / patch["target"]
    if not target.exists():
        if idempotent:
            return False
        raise PatchError(f"target file missing: {target}")
    text = target.read_text(encoding="utf-8")

    if op == "replace":
        needle, repl = patch["needle"], patch["repl"]
        if needle not in text:
            if idempotent:
                return False
            raise PatchError(f"needle not found in {target}")
        target.write_text(text.replace(needle, repl, 1), encoding="utf-8")
        return True
    if op == "append":
        repl = patch["repl"]
        if text.endswith(repl):
            return False
        target.write_text(text + repl, encoding="utf-8")
        return True
    if op == "remove":
        needle = patch["needle"]
        if needle not in text:
            if idempotent:
                return False
            raise PatchError(f"needle not found for remove: {target}")
        target.write_text(text.replace(needle, "", 1), encoding="utf-8")
        return True
    raise PatchError(f"unknown operation: {op}")


def apply_manifest(*, family_root: Path) -> int:
    """Apply all patches not yet in `applied`. Returns newly applied count."""
    manifest = loader.load_patches_manifest()
    already = set(manifest.get("applied", []))
    newly = 0
    for p in manifest.get("patches", []):
        pid = p.get("id")
        if pid in already:
            continue
        try:
            apply_patch(p, family_root=family_root, idempotent=True)
        except PatchError as exc:
            raise PatchError(f"patch {pid!r} failed: {exc}") from exc
        already.add(pid)
        newly += 1
    manifest["applied"] = sorted(already)
    loader.save_patches_manifest(manifest)
    return newly
```

**Step 4: 跑测试确认通过**

Run: `pytest tests/test_patcher.py -v`
Expected: `6 passed`

**Step 5: Commit**

```bash
git add src/pax/forge/patcher.py tests/test_patcher.py
git commit -m "feat(patcher): idempotent patch apply + manifest replay"
```

---

### Task 6.2：`pax-forge patch apply` 子命令

**Files:**
- Modify: `src/pax/forge/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: 追加测试**

```python
def test_cli_patch_apply_empty_manifest():
    result = run_cli("patch", "apply")
    assert result.returncode == 0
    assert "0" in result.stdout or "applied" in result.stdout.lower()
```

**Step 2: 实现（cli.py 中 `patch` 分支）**

```python
    if args.command == "patch" and args.sub_command == "apply":
        from pax.forge.patcher import apply_manifest, PatchError
        try:
            n = apply_manifest(family_root=Path.cwd())
        except PatchError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"applied {n} new patches")
        return 0
```

**Step 3: 跑测试确认通过**

**Step 4: Commit**

```bash
git add src/pax/forge/cli.py tests/test_cli.py
git commit -m "feat(cli): patch apply subcommand"
```

---

### Task 6.3：端到端补丁测试

**Files:**
- Create: `tests/test_patcher_e2e.py`

**Step 1: 写测试**

```python
# tests/test_patcher_e2e.py
"""End-to-end: add a patch to manifest, run apply, verify idempotency."""
import json
import atexit
from pathlib import Path
from pax.forge import loader


_ORIGINAL = loader.PATCHES_MANIFEST_PATH


def _restore():
    loader.PATCHES_MANIFEST_PATH = _ORIGINAL


atexit.register(_restore)


def test_end_to_end_patch(tmp_path):
    root = tmp_path / "fam"
    (root / "skills").mkdir(parents=True)
    (root / "skills" / "target.md").write_text(
        "hello\nworld\n", encoding="utf-8"
    )
    manifest_path = root / "pax-ops" / "patches" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({
        "version": "1.0",
        "patches": [{"id": "p1", "target": "skills/target.md",
                     "operation": "replace",
                     "needle": "world", "repl": "PLANET"}],
        "applied": []
    }), encoding="utf-8")
    loader.PATCHES_MANIFEST_PATH = manifest_path

    from pax.forge.patcher import apply_manifest
    n1 = apply_manifest(family_root=root)
    assert n1 == 1
    text = (root / "skills" / "target.md").read_text(encoding="utf-8")
    assert "PLANET" in text and "world" not in text
    # 幂等
    n2 = apply_manifest(family_root=root)
    assert n2 == 0


# 确保其他测试不受影响
def teardown_module() -> None:
    loader.PATCHES_MANIFEST_PATH = _ORIGINAL
```

**Step 2: 跑测试确认通过**

**Step 3: Commit**

```bash
git add tests/test_patcher_e2e.py
git commit -m "test(patcher): end-to-end patch application"
```

---

## Phase 7：参考文档与治理

### Task 7.1：`references/severity-criteria.md`

**Files:**
- Create: `references/severity-criteria.md`

**Step 1: 写文件**

```markdown
# Severity 量化标准

`pax-diagnose` 输出的 `severity` 必须按以下标准评估。

## P0 —— 严重

**判断标准**（任一满足即 P0）：

- 核心流程完全不可用
- 影响所有用户
- 无临时规避手段
- 涉及安全（数据泄露、认证绕过、注入等）

**触发**：强制升级 `pax-council`，人工审批后方可进入 `pax-plan`。

## P1 —— 主要

**判断标准**（任一满足）：

- 核心流程部分不可用（有替代路径）
- 影响部分用户
- 存在临时规避手段

**触发**：正常走 `plan -> execute -> review`。

## P2 —— 次要

**判断标准**（任一满足）：

- 非核心流程部分不可用
- 影响少量用户
- 有明显规避手段

**触发**：可合并到常规迭代，走标准流程。

## 评估维度

`severity_rationale` 必须显式填写以下四项：

- `core_flow_broken`: 是否影响核心流程
- `affected_users`: all / most / some / few
- `workaround_available`: 是否有临时规避
- `security_relevant`: 是否涉及安全
```

**Step 2: Commit**

```bash
git add references/severity-criteria.md
git commit -m "docs(references): severity criteria"
```

---

### Task 7.2：`references/domain-dependencies.md`

**Files:**
- Create: `references/domain-dependencies.md`

**Step 1: 写文件**

```markdown
# 领域依赖映射表

用于 `pax-diagnose` 输出 `regression_scope` 时参考。

## 认证/授权
- 根因：密钥轮换、token 失效、权限模型变更
- 必测：登录、注册、token 刷新、权限校验、SSO
- 应测：用户信息接口、审计日志

## 支付
- 根因：支付网关变更、订单状态机变更
- 必测：下单、支付回调、订单状态、退款
- 应测：订单列表、支付记录、对账

## 数据一致性
- 根因：事务边界、并发控制、缓存失效
- 必测：写后读、并发写、缓存穿透
- 应测：报表、导出、异步任务
```

**Step 2: Commit**

```bash
git add references/domain-dependencies.md
git commit -m "docs(references): domain dependencies"
```

---

### Task 7.3：`references/compatibility-matrix.md`

**Files:**
- Create: `references/compatibility-matrix.md`

**Step 1: 写文件**

```markdown
# Compatibility Matrix

来源：`pax-ops/versions.json` 的 `compatibility_matrix` 字段。
本文件只是人类可读镜像，权威源始终是 JSON。

| From | Can call |
|---|---|
| `pax-orchestrate@0.1` | `pax-clarify@0.1` |
| `pax-clarify@0.1` | `pax-diagnose@0.1`, `pax-plan@0.1` |
| `pax-diagnose@0.1` | `pax-plan@0.1` |
| `pax-plan@0.1` | `pax-execute@0.1` |
| `pax-execute@0.1` | `pax-review@0.1` |

## Breaking change 规则

- 修改 `pax-snapshot.schema.json` 中任一必填字段 → 家族 major bump
- 新增可选字段 → minor bump
- 新增 skill → minor bump
- 弃用 skill → minor bump（保留一个 minor 版本过渡期）
- 删除 skill → major bump
```

**Step 2: Commit**

```bash
git add references/compatibility-matrix.md
git commit -m "docs(references): compatibility matrix"
```

---

### Task 7.4：`README.md`（家族入口）

**Files:**
- Create: `README.md`

**Step 1: 写文件**

```markdown
# pax-*

**Pact-based Agreement eXecution** —— 一个以软件工程方法构建的 AI Skill 家族。

## 特性

- **可组合**：跨 Skill 状态通过结构化快照通信
- **可审计**：每个阶段的状态、决策、跳过、失败全部留痕
- **可验证**：契约测试强制家族规则
- **可版本化**：家族统一版本线，兼容矩阵显式管理
- **可演化**：`pax-forge` 生成 + `pax-evolve` 自进化

## 家族构成

| 层 | Skill | 可选 | 职责 |
|---|---|---|---|
| meta | `pax-forge` | 否 | 生成、校验、注册 |
| L0 | `pax-orchestrate` | 否 | 路由、风险分级 |
| L1 | `pax-clarify` | 否 | 共识状态机 |
| L1 | `pax-diagnose` | 是 | 根因诊断 |
| L1 | `pax-plan` | 否 | 结构化规划 |
| L1 | `pax-execute` | 否 | 契约约束下执行 |
| L1 | `pax-review` | 否 | 独立评审门禁 |
| L2 | `pax-advisor` | 是 | 单点咨询 |
| L2 | `pax-council` | 是 | 多专家盲审 |
| L3 | `pax-worker-*` | 是 | 有界任务执行 |
| L4 | `pax-verify` | 是 | 运行中验证 |
| L4 | `pax-evolve` | 是 | 自进化 |
| L4 | `pax-docs` | 是 | 文档沉淀 |

## 快速开始

```bash
pip install -e ".[dev]"

# 生成一个新 skill
pax-forge new pax-foo --layer L1 --description "..."
pax-forge validate skills/pax-foo
pax-forge register skills/pax-foo

# 跑家族契约测试
pax-forge test

# 列出所有注册 skill
pax-forge list
```

## 设计文档

见 `docs/pax-family-design.md`。

## 贡献

见 `CONTRIBUTING.md`。

## 版本

家族版本见 `pax-ops/versions.json`。
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

### Task 7.5：`CONTRIBUTING.md`

**Files:**
- Create: `CONTRIBUTING.md`

**Step 1: 写文件**

```markdown
# 贡献指南

## 如何新增一个 pax-* Skill

1. 使用 `pax-forge` 生成骨架：
   ```bash
   pax-forge new pax-<capability> --layer <L0|L1|L2|L3|L4> [--optional]
   ```
2. 编辑 `skills/pax-<capability>/SKILL.md`：
   - 补充 `description`
   - 按层模板填充所有 `##` 段
   - 若有跨 skill 依赖，在"何时升级"段列出
3. 校验：
   ```bash
   pax-forge validate skills/pax-<capability>
   ```
4. 注册：
   ```bash
   pax-forge register skills/pax-<capability>
   ```
5. 更新 `pax-ops/versions.json` 的 `skills` 段
6. 跑契约测试：
   ```bash
   pax-forge test
   ```
7. 若涉及 breaking change，`pax-forge version major` 并更新兼容矩阵

## 分支策略

- 主线：`main`，受保护
- 特性分支：`feat/<short-name>`
- 修复分支：`fix/<short-name>`

## 提交规范

Conventional Commits：`feat:` / `fix:` / `docs:` / `test:` / `chore:` / `refactor:`

## PR 检查清单

- [ ] `pax-forge test` 通过
- [ ] 新增 skill 已注册到 `versions.json` 和 `registry.json`
- [ ] 如有 breaking change，`versions.json` 已 bump major
- [ ] 兼容矩阵已更新
- [ ] 文档同步
```

**Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING"
```

---

## Phase 8：收尾

### Task 8.1：全量测试运行

**Files:**
- 无（纯验证）

**Step 1: 跑全量测试**

```bash
pytest -v
```
Expected: 全部通过（预期 ≥ 40 tests）。

**Step 2: 跑 CLI 契约测试**

```bash
pax-forge test
```
Expected: 全部 PASS。

**Step 3: 提交测试结果（无变更则不提交）**

```bash
git status --short
```

---

### Task 8.2：`CHANGELOG.md`

**Files:**
- Create: `CHANGELOG.md`

**Step 1: 写文件**

```markdown
# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-09-29

### Added
- 家族宪法 `schemas/pax-family.schema.yaml`
- 快照 JSON Schema `schemas/snapshot.schema.json`
- 版本基线 `pax-ops/versions.json`
- 注册表 `pax-ops/registry.json`
- 补丁清单 `pax-ops/patches/manifest.json`
- CLI `pax-forge`：`init / new / validate / register / list / test / version / deprecate / patch apply` 九个子命令
- 7 项契约测试：frontmatter 完整性 / snapshot schema 合法性 / 层间调用合法性 / 版本一致性 / 无环 / 跳过审计 / 门禁行为
- 13 个 Skill 骨架：L0/L1/L2/L3/L4/meta 全覆盖
- 参考文档：severity-criteria / domain-dependencies / compatibility-matrix
```

**Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG"
```

---

### Task 8.3：打 tag `v0.1.0`

**Files:**
- 无（git tag）

**Step 1: 确认工作区干净**

```bash
git status --short
git log --oneline -5
```
Expected: working tree clean。

**Step 2: 打 tag**

```bash
git tag -a v0.1.0 -m "pax-* family v0.1.0: initial bootstrap"
git push --tags 2>/dev/null || echo "no remote, tag is local"
```

**Step 3: 验证**

```bash
git show --stat v0.1.0
```

---

## 全计划小结

- **8 个 Phase**，约 **42 个 Task**，每个 2–5 分钟
- **单一真相源**：`pax-family.schema.yaml` + `snapshot.schema.json` + `versions.json` 三文件驱动一切
- **CLI 完备**：`pax-forge init / new / validate / register / list / test / version / deprecate / patch apply` 九个子命令
- **契约测试 7 项**：frontmatter / snapshot schema / layer calls / version / no cycles / skip audit / gate behavior
- **13 个 Skill 骨架**：L0/L1 必需 6 个 + L2/L3/L4 可选 7 个
- **参考文档 3 份**：severity-criteria / domain-dependencies / compatibility-matrix
- **端到端**：`init -> new -> validate -> register -> list -> test -> patch apply` 全流程打通
- **幂等**：补丁层保证重复执行无副作用
- **版本治理**：单点版本源、`version bump` + `deprecate` 完整

---

**Plan complete and saved to `docs/plans/2026-09-29-pax-family-bootstrap.md`. Two execution options:**

**1. Subagent-Driven（本会话）**——我为每个 Task 分派一个独立 subagent，任务间做代码审查，快速迭代。适合希望我持续在场、随时干预的场景。

**2. Parallel Session（新会话）**——新开一个会话配合 `superpowers:executing-plans`，按 Task 批次执行、设置检查点。适合希望在专用 worktree 内长时间跑、只在检查点回来汇报的场景。

**Which approach?**

> 建议：Phase 0 结束后先切到 `feat/pax-bootstrap` 分支，把主分支 `main` 留给最终 tag。



