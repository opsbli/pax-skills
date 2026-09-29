"""Cross-skill contract test suite for pax-* family."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest


# ----- 框架占位测试 -----

def test_contract_report_start_empty():
    from pax.forge.contracts import ContractReport
    r = ContractReport()
    assert r.ok
    assert r.failures == []


def test_run_all_contracts_returns_report(tmp_path):
    # 框架级检查：run_all_contracts 应返回 ContractReport 实例
    # （早期版本以空 registry 作为无契约场景，注册首个契约后不再适用）
    from pax.forge.contracts import (
        ContractReport, list_contracts, run_all_contracts,
    )
    (tmp_path / "skills").mkdir(parents=True, exist_ok=True)
    report = run_all_contracts(tmp_path)
    assert isinstance(report, ContractReport)
    assert isinstance(list_contracts(), list)


# ----- 契约①：frontmatter 完整性 -----

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
    assert any("description" in v or "version" in v for v in violations)


def test_contract_frontmatter_completeness_passes_clean(tmp_path, monkeypatch):
    from pax.forge.contracts import check_frontmatter_completeness
    from pax.forge import loader
    # 复制真实 schema
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


# ----- 契约②：snapshot schema 合法性 -----

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


# ----- 契约③：层间调用合法性 -----

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


# ----- 契约④：版本一致性 -----

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


# ----- 契约⑤：无循环依赖 -----

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
