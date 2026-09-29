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
