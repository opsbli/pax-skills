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


def test_register_contract_decorator_registers_name():
    """@register_contract(name) must store the function under ``name``."""
    from pax.forge.contracts import _CONTRACTS, list_contracts, register_contract

    marker = "__framework_test_contract__"
    try:
        @register_contract(marker)
        def _dummy(family_root):
            return []

        assert marker in _CONTRACTS
        assert marker in list_contracts()
    finally:
        _CONTRACTS.pop(marker, None)


def test_list_contracts_returns_sorted_names():
    from pax.forge.contracts import _CONTRACTS, list_contracts, register_contract

    saved = dict(_CONTRACTS)
    _CONTRACTS.clear()
    try:
        @register_contract("zeta")
        def _z(family_root): return []

        @register_contract("alpha")
        def _a(family_root): return []

        assert list_contracts() == ["alpha", "zeta"]
    finally:
        _CONTRACTS.clear()
        _CONTRACTS.update(saved)


def test_run_all_contracts_catches_contract_exceptions(tmp_path):
    """A contract that raises must not abort the run; failures accumulate."""
    from pax.forge.contracts import (
        _CONTRACTS, register_contract, run_all_contracts,
    )

    saved = dict(_CONTRACTS)
    _CONTRACTS.clear()
    try:
        @register_contract("__boom__")
        def _boom(family_root):
            raise RuntimeError("kaboom")

        (tmp_path / "skills").mkdir(parents=True, exist_ok=True)
        report = run_all_contracts(tmp_path)
        assert not report.ok
        assert any("kaboom" in f for f in report.failures)
    finally:
        _CONTRACTS.clear()
        _CONTRACTS.update(saved)


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


# ----- 契约⑥：跳过审计 -----

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


# ----- 契约⑦：门禁行为 -----

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


def test_contract_gate_refusal_l0_forced_missing_refuse(tmp_path):
    """L0 强制入口（orchestrate）门禁段落没有拒绝语义，仅「降级继续」→ 违规。"""
    from pax.forge.contracts import check_gate_refusal
    d = tmp_path / "skills" / "pax-orchestrate"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-orchestrate\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L0\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-orchestrate\n## Execution Contract\n"
        "- 前置门禁：能读取 pax-family.schema.yaml 与 pax-ops/versions.json\n"
        "- 门禁失败：降级后继续执行，不阻塞任务\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    violations = check_gate_refusal(tmp_path)
    assert any("pax-orchestrate" in v for v in violations)


def test_contract_gate_refusal_l0_forced_passes_with_refuse(tmp_path):
    """L0 强制入口门禁段落含「拒绝启动/返回 blocked」→ 通过。"""
    from pax.forge.contracts import check_gate_refusal
    d = tmp_path / "skills" / "pax-orchestrate"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-orchestrate\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L0\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-orchestrate\n## Execution Contract\n"
        "- 前置门禁：能读取 pax-family.schema.yaml 与 pax-ops/versions.json\n"
        "- 未通过门禁：拒绝启动，返回用户错误\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    assert check_gate_refusal(tmp_path) == []


def test_contract_gate_refusal_degrade_without_refuse(tmp_path):
    """非 L0 skill 声明门禁但只写降级继续、无拒绝语义 → 违规。"""
    from pax.forge.contracts import check_gate_refusal
    d = tmp_path / "skills" / "pax-plan"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-plan\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-plan\n## Execution Contract\n"
        "- 前置门禁：consensus.gaps_remaining == []\n"
        "- 门禁失败：降级继续执行，不阻塞\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    violations = check_gate_refusal(tmp_path)
    assert any("pax-plan" in v for v in violations)


def test_contract_gate_refusal_ignores_skill_without_gate_decl(tmp_path):
    """段落未声明门禁但含拒绝/降级词时，不触发本契约（由 gate-behavior 管）。"""
    from pax.forge.contracts import check_gate_refusal
    d = tmp_path / "skills" / "pax-plan"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-plan\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-plan\n## Execution Contract\n"
        "- 步骤一：先做 X\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n",
        encoding="utf-8",
    )
    assert check_gate_refusal(tmp_path) == []


# ----- 汇总：契约注册集合 -----

def test_all_contracts_registered():
    from pax.forge.contracts import list_contracts
    # 强制 import contracts 以注册
    import pax.forge.contracts  # noqa
    names = set(list_contracts())
    expected = {
        "frontmatter-completeness",
        "snapshot-schema-validity",
        "snapshot-field-conformance",
        "layer-call-legality",
        "layer-membership",
        "compatibility-matrix-consistency",
        "version-consistency",
        "no-cycles",
        "skip-audit",
        "gate-behavior",
        "gate-refusal",
        "declared-checks-coverage",
    }
    assert names == expected


def test_declared_checks_match_family_schema():
    """schema.contracts.declared_checks 必须与实现一致（双向）。"""
    from pax.forge import loader
    from pax.forge.contracts import list_contracts
    import pax.forge.contracts  # noqa
    declared = set(loader.load_family_schema()["contracts"]["declared_checks"])
    implemented = set(list_contracts()) - {"declared-checks-coverage"}
    assert declared == implemented


# ----- 新增契约的负向用例：确实能抓到漂移 -----

def _fake_family(tmp_path):
    """构造一个被当作 family root 的临时家族（含 schema + versions + registry）。"""
    import json
    import shutil
    from pax.forge import loader
    (tmp_path / "schemas").mkdir(parents=True, exist_ok=True)
    shutil.copy(loader.FAMILY_SCHEMA_PATH,
                tmp_path / "schemas" / "pax-family.schema.yaml")
    shutil.copy(loader.SNAPSHOT_SCHEMA_PATH,
                tmp_path / "schemas" / "snapshot.schema.json")
    (tmp_path / "pax-ops").mkdir(exist_ok=True)
    (tmp_path / "pax-ops" / "versions.json").write_text(
        json.dumps({"family": "pax", "version": "1.0.0", "skills": {}}),
        encoding="utf-8",
    )
    (tmp_path / "pax-ops" / "registry.json").write_text(
        json.dumps({"family": "pax", "updated_at": "x", "skills": [
            {"name": "pax-ghost", "layer": "L1", "optional": False,
             "version": "1.0.0", "path": "skills/pax-ghost/SKILL.md",
             "registered_at": "x"}
        ]}),
        encoding="utf-8",
    )
    d = tmp_path / "skills" / "pax-ghost"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-ghost\ndescription: >\n  x\nversion: 1.0.0\n"
        "family: pax\nlayer: L1\noptional: false\nrequires_snapshot: true\n---\n\n"
        "# pax-ghost\n\n"
        "写入 `snapshot.bogus_section` 与 `snapshot.execution.nope`\n\n"
        "## Execution Contract\n- 前置门禁：x\n## 职责边界\n- x\n## 输入\n- x\n"
        "## 工作流\n1. x\n## 输出契约\n- x\n## 失败模式\n- x\n## 何时升级\n- x\n",
        encoding="utf-8",
    )


def test_snapshot_field_conformance_catches_unknown_section(tmp_path):
    from pax.forge.contracts import check_snapshot_field_conformance
    _fake_family(tmp_path)
    v = check_snapshot_field_conformance(tmp_path)
    assert any("bogus_section" in x for x in v)


def test_snapshot_field_conformance_catches_unknown_subfield(tmp_path):
    from pax.forge.contracts import check_snapshot_field_conformance
    _fake_family(tmp_path)
    v = check_snapshot_field_conformance(tmp_path)
    assert any("execution.nope" in x for x in v)


def test_layer_membership_catches_undeclared_skill(tmp_path):
    from pax.forge.contracts import check_layer_membership
    _fake_family(tmp_path)
    v = check_layer_membership(tmp_path)
    assert any("pax-ghost" in x for x in v)


def test_compatibility_matrix_consistency_catches_unknown_layer(tmp_path):
    import json
    from pax.forge.contracts import check_compatibility_matrix_consistency
    _fake_family(tmp_path)
    reg = json.loads((tmp_path / "pax-ops" / "registry.json").read_text(encoding="utf-8"))
    reg["skills"] = []
    (tmp_path / "pax-ops" / "registry.json").write_text(
        json.dumps(reg), encoding="utf-8")
    (tmp_path / "pax-ops" / "versions.json").write_text(
        json.dumps({"family": "pax", "version": "1.0.0", "skills": {},
                    "compatibility_matrix": {"L9": ["L1"]}}),
        encoding="utf-8",
    )
    v = check_compatibility_matrix_consistency(tmp_path)
    assert any("L9" in x for x in v)


def test_allowed_calls_reads_versions_matrix():
    """_allowed_calls 必须从 versions.json 读，而不是代码里硬编码。"""
    from pax.forge import loader
    from pax.forge.contracts import _allowed_calls
    matrix = loader.load_versions()["compatibility_matrix"]
    expected = {(src, tgt) for src, targets in matrix.items()
                if not src.startswith("_") for tgt in targets}
    assert _allowed_calls() == expected
