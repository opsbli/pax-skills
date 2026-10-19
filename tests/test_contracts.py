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
    def write(name: str, layer: str, forward: str = "", escalate: str = ""):
        d = tmp_path / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: >\n  x\nversion: 0.1.0\n"
            f"family: pax\nlayer: {layer}\noptional: false\n"
            f"requires_snapshot: true\n---\n\n# {name}\n"
            f"## Execution Contract\n- x\n## 职责边界\n- x\n## 输入\n- x\n"
            f"## 工作流\n1. x\n{forward}\n## 输出契约\n- x\n## 失败模式\n- x\n"
            f"## 何时升级\n{escalate}\n",
            encoding="utf-8",
        )
    # L4 前向调用 L1 应该被标记（compatibility_matrix 不允许 L4 -> L1）
    write("pax-v", "L4", forward="1. 调用 `pax-plan`")
    write("pax-plan", "L1")
    violations = check_layer_call_legality(tmp_path)
    assert any("pax-v" in v for v in violations)


def test_layer_call_legality_ignores_escalation_edges(tmp_path):
    """失败回退到更上游的层不报非法方向（L1 测试失败退回 L1 plan 是设计闭环）。"""
    from pax.forge.contracts import check_layer_call_legality
    d = tmp_path / "skills" / "pax-v"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-v\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L4\noptional: false\n"
        "requires_snapshot: true\n---\n\n# pax-v\n"
        "## 工作流\n1. x\n## 何时升级\n- 失败 → `pax-plan`\n",
        encoding="utf-8",
    )
    assert check_layer_call_legality(tmp_path) == []


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
    """前向调用边成环 → 必须报出。

    调用声明写在正文（动词 + 反引号包裹的 skill 名），不放进
    `## 何时升级` —— 后者是失败回退边，按设计不参与环检测
    （见 test_no_cycles_ignores_escalation_edges）。
    """
    from pax.forge.contracts import check_no_cycles
    _mk_skill(tmp_path, "pax-a", "## 工作流\n1. 调用 `pax-b`")
    _mk_skill(tmp_path, "pax-b", "## 工作流\n1. 调用 `pax-a`")
    violations = check_no_cycles(tmp_path)
    assert any("cycle" in v.lower() for v in violations)


def test_no_cycles_ignores_escalation_edges(tmp_path):
    """仅失败回退成环不算环——测试失败退回 plan 是设计要求的闭环。"""
    from pax.forge.contracts import check_no_cycles
    _mk_skill(tmp_path, "pax-a", "## 何时升级\n- 失败 → `pax-b`")
    _mk_skill(tmp_path, "pax-b", "## 何时升级\n- 失败 → `pax-a`")
    assert check_no_cycles(tmp_path) == []


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
        "router-coverage",
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


# ----- 契约⑬：router-coverage -----

def _write_entry_with_routing_table(tmp_path, rows, extra=""):
    """构造一个含路由表的 pax-orchestrate，外加 registry/versions/schema。"""
    import json
    import yaml

    from pax.forge import loader as _loader

    body = (
        "---\nname: pax-orchestrate\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L0\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-orchestrate\n\n## Execution Contract\n"
        "- 前置门禁：无\n- 门禁失败：拒绝启动\n"
        "## 职责边界\n- ...\n## 输入\n- ...\n## 工作流\n1. ...\n"
        "## 输出契约\n- ...\n## 失败模式\n- ...\n## 何时升级\n- ...\n"
        + extra
        + "\n#### 代表路由组合\n\n"
        "| 一级意图 | 二级意图 | diagnose_required | 路由 | 标注 |\n"
        "|---|---|---|---|---|\n"
        + rows
    )
    d = tmp_path / "skills" / "pax-orchestrate"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")

    (tmp_path / "pax-ops").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pax-ops" / "registry.json").write_text(
        json.dumps({"family": "pax", "skills": [
            {"name": "pax-orchestrate", "layer": "L0", "optional": False},
            {"name": "pax-clarify", "layer": "L1", "optional": False},
            {"name": "pax-monitor", "layer": "L1", "optional": True},
        ]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "pax-ops" / "versions.json").write_text(
        json.dumps({"family": "pax", "version": "1.0.0", "skills": {},
                    "compatibility_matrix": {"L0": ["L1"], "L1": ["L1"]}}),
        encoding="utf-8")
    (tmp_path / "schemas").mkdir(parents=True, exist_ok=True)
    real = dict(_loader.load_family_schema())
    real.setdefault("non_runtime_layers", [])
    (tmp_path / "schemas" / "pax-family.schema.yaml").write_text(
        yaml.safe_dump(real, allow_unicode=True), encoding="utf-8")


def test_contract_router_coverage_all_present_passes(tmp_path):
    """路由表覆盖全部 L1 成员 → 通过。"""
    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify, monitor]` | — |\n",
    )
    assert check_router_coverage(tmp_path) == []


def test_contract_router_coverage_missing_skill_flags(tmp_path):
    """L1 成员未出现在路由表 → 违规（这是契约的主要 teeth）。"""
    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify]` | — |\n",
    )
    violations = check_router_coverage(tmp_path)
    assert any("pax-monitor" in v for v in violations)
    assert not any("pax-clarify" in v for v in violations)


def test_contract_router_coverage_ignores_description_mentions(tmp_path):
    """skill 名只出现在正文说明、路由表里没有 → 仍须违规。

    这是防「扫全文代替扫路由表」的回归用例：早期实现扫全文，
    pax-clarify 在 description 里出现 7 处，导致路由表删光也不报。
    """
    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify]` | — |\n",
        extra="\n本 skill 会调用 pax-monitor 与 pax-clarify 完成监控与澄清。\n",
    )
    violations = check_router_coverage(tmp_path)
    assert any("pax-monitor" in v for v in violations)


def test_contract_router_coverage_ignores_embedded_gate_skill(tmp_path):
    """pax-gate 是内嵌门禁段，不作为独立路由落点 → 不报。"""
    import json

    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify, monitor]` | — |\n",
    )
    reg = tmp_path / "pax-ops" / "registry.json"
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["skills"].append(
        {"name": "pax-gate", "layer": "L1", "optional": True})
    reg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert check_router_coverage(tmp_path) == []


def test_contract_router_coverage_ignores_deeper_layers(tmp_path):
    """L2/L3/L4 由上层委派或用户直调，不属于入口路由 → 不报。"""
    import json

    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify, monitor]` | — |\n",
    )
    reg = tmp_path / "pax-ops" / "registry.json"
    data = json.loads(reg.read_text(encoding="utf-8"))
    for name, layer in [
        ("pax-advisor", "L2"), ("pax-worker-implement", "L3"),
        ("pax-init", "L4"),
    ]:
        data["skills"].append(
            {"name": name, "layer": layer, "optional": True})
    reg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert check_router_coverage(tmp_path) == []


def test_contract_router_coverage_ignores_self(tmp_path):
    """入口自己不在自己的路由表里 → 不报。"""
    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify, monitor]` | — |\n",
    )
    assert not any(
        "pax-orchestrate" in v for v in check_router_coverage(tmp_path))


def test_contract_router_coverage_missing_table_flags(tmp_path):
    """路由表区段缺失 → 契约自身报出（不能静默判绿）。"""
    from pax.forge.contracts import check_router_coverage
    d = tmp_path / "skills" / "pax-orchestrate"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-orchestrate\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L0\noptional: false\nrequires_snapshot: true\n"
        "---\n\n# pax-orchestrate\n\n没有路由表。\n",
        encoding="utf-8",
    )
    violations = check_router_coverage(tmp_path)
    assert any("未找到路由声明区段" in v for v in violations)


def test_routing_table_segment_stops_at_first_non_row():
    """区段提取必须在表格结束处停下，不得吞掉后续正文。"""
    from pax.forge.contracts import _routing_table_segment
    body = (
        "| 一级意图 | 路由 |\n|---|---|\n| a | `[clarify]` |\n"
        "\n## 后续章节\n这里提到 pax-monitor，不属于路由表。\n"
    )
    seg = _routing_table_segment(body)
    assert seg is not None
    assert "pax-monitor" not in seg
    assert "[clarify]" in seg


def test_contract_router_coverage_accepts_optional_skill_table(tmp_path):
    """skill 只登记在「可选 Skill」表也算被路由声明覆盖。

    回归用例：pax-orchestrate 有两张表——`代表路由组合` 与
    `除主路由外，以下可选 Skill ...`。monitor / rollback / deploy /
    learn / design / research / prototype-to-prd 全登记在第二张表。
    早期实现只看第一张，把这7 个全判成缺口。
    """
    import json

    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify]` | — |\n",
    )
    # 在主路由表之后追加可选 skill 表，登记 monitor
    d = tmp_path / "skills" / "pax-orchestrate"
    body = (d / "SKILL.md").read_text(encoding="utf-8")
    body += (
        "\n除主路由外，以下可选 Skill 可在特定条件下被调用：\n\n"
        "| Skill | 层级 | 触发条件 | 说明 |\n|---|---|---|---|\n"
        "| `pax-monitor` | L1 | 任务执行中 | 监控异常 |\n"
    )
    (d / "SKILL.md").write_text(body, encoding="utf-8")
    assert check_router_coverage(tmp_path) == []


def test_contract_router_coverage_flags_when_absent_from_both_tables(tmp_path):
    """两张表都没有该 skill → 必须报（证明上一条不是恒真）。

    fixture 只写了主路由表（`[clarify]`），没有可选 skill 表，
    monitor 因此确实未被声明，应当报出。
    """
    from pax.forge.contracts import check_router_coverage
    _write_entry_with_routing_table(
        tmp_path,
        "| `feature_dev` | — | false | `[clarify]` | — |\n",
    )
    assert any("pax-monitor" in v for v in check_router_coverage(tmp_path))


# ----- 元数据引用不得计入调用图（A 方案）-----

def test_strip_metadata_fields_removes_inline_array_value():
    """行内数组形态的元数据字段，其值不得残留。"""
    from pax.forge.contracts import strip_metadata_fields
    body = '正常正文 pax-execute 调用\napplies_to: ["pax-plan P2", "pax-review R1"]\n后续正文\n'
    out = strip_metadata_fields(body)
    assert "pax-review" not in out
    assert "pax-execute" in out
    assert "后续正文" in out


def test_strip_metadata_fields_removes_indented_list_items():
    """缩进列表形态：字段名与其后的 `- "..."` 项必须一起删。

    回归用例：只删字段名那一行时，`- "pax-plan P2 / P7"` 仍会被
    `_mentioned_skills`扫成调用边，误报原样存在。
    """
    from pax.forge.contracts import strip_metadata_fields
    body = (
        "正文\n"
        "      applies_to:\n"
        "        - \"pax-plan P2 / P7\"\n"
        "        - \"pax-execute E3 / E4\"\n"
        "      status: review\n"
        "结尾正文\n"
    )
    out = strip_metadata_fields(body)
    assert "pax-plan" not in out
    assert "pax-execute" not in out
    assert "status: review" in out
    assert "正文" in out


def test_strip_metadata_fields_removes_block_scalar_body():
    """block scalar 形态（`rationale: |`）的正文也要删。"""
    from pax.forge.contracts import strip_metadata_fields
    body = (
        "正文\n"
        "      rationale: |\n"
        "        若 plan.steps 为空，pax-execute E4 无锚点可追踪，\n"
        "        pax-plan P2 无法镜像。\n"
        "      status: review\n"
    )
    out = strip_metadata_fields(body)
    assert "pax-execute" not in out
    assert "pax-plan" not in out
    assert "status: review" in out


def test_strip_metadata_fields_keeps_real_declarations():
    """真实调用声明不得被元数据剔除逻辑误删。

    「由 pax-orchestrate 委托调用」是description 里的合法声明；
    若按区块删除元数据会连带丢掉它。
    """
    from pax.forge.contracts import strip_metadata_fields
    body = (
        "由 pax-orchestrate 在评审阶段委托调用 pax-advisor。\n"
        "      applies_to:\n"
        "        - \"pax-review R1\"\n"
    )
    out = strip_metadata_fields(body)
    assert "pax-orchestrate" in out
    assert "pax-advisor" in out
    assert "pax-review" not in out


def test_call_targets_excludes_metadata_but_keeps_prose():
    """_call_targets 排除元数据引用，保留正文声明。"""
    from pax.forge.contracts import _call_targets
    body = (
        "调用 pax-execute 执行。\n"
        "      applies_to:\n"
        "        - \"pax-plan P2\"\n"
    )
    targets = _call_targets(body, "pax-evolve")
    assert "pax-execute" in targets
    assert "pax-plan" not in targets


def test_call_graph_ignores_metadata_only_references(tmp_path):
    """仅通过 applies_to 提及别的 skill，不构成调用边（no-cycles 的 teeth）。"""
    from pax.forge.contracts import _extract_call_graph
    d = tmp_path / "skills" / "pax-evolve"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-evolve\ndescription: >\n  x\nversion: 0.1.0\n"
        "family: pax\nlayer: L4\noptional: true\nrequires_snapshot: true\n"
        "---\n\n# pax-evolve\n\n"
        "本skill 由编排层委托，不调用其他 skill。\n\n"
        "experience_library:\n"
        "  entries:\n"
        "    - id: E101\n"
        "      applies_to:\n"
        '        - "pax-plan P2 / P7"\n'
        '        - "pax-execute E3 / E4"\n'
        "      status: review\n",
        encoding="utf-8",
    )
    graph = _extract_call_graph(tmp_path)
    assert graph["pax-evolve"] == set()


def test_all_contracts_green_on_real_family():
    """全部契约必须在**真实家族**上同时为绿。

    回归用例（结构性盲区）：此前 tests/test_contracts.py 里每个契约的
    测试都用 tmp_path 构造的单文件假家族，从不跑真实家族。
    于是 `pax-evolve` 新增 E101-E104 经验条目（其中 applies_to 引用了
    多个 skill）时，真实家族上no-cycles / layer-call-legality 共报出41条
    违规，而 pytest 全绿——没有任何测试能发现。

    这条测试把「真实家族全绿」变成硬门禁：任何人往 skills/ 加内容
    导致契约变红，pytest 会立刻失败，而不是等到 CI 或人工 review。
    """
    from pathlib import Path

    from pax.forge import loader
    from pax.forge.contracts import run_all_contracts

    family_root = Path(__file__).resolve().parents[1]
    if not (family_root / "pax-ops" / "registry.json").exists():
        pytest.skip("不是家族仓库，跳过")

    report = run_all_contracts(family_root)
    assert report.ok, (
        f"真实家族上契约未全绿（{len(report.failures)} 条）：\n"
        + "\n".join(report.failures[:20])
        + ("\n… 其余见run_all_contracts 输出" if len(report.failures) > 20 else "")
    )


def test_real_family_matches_schema_declared_checks():
    """真实家族的 declared_checks 与实现一致（真实数据版，非 fixture）。"""
    from pathlib import Path

    from pax.forge import loader
    from pax.forge.contracts import list_contracts

    family_root = Path(__file__).resolve().parents[1]
    if not (family_root / "pax-ops" / "registry.json").exists():
        pytest.skip("不是家族仓库，跳过")

    declared = set(
        loader.load_family_schema(family_root=family_root)["contracts"]["declared_checks"]
    )
    implemented = set(list_contracts()) - {"declared-checks-coverage"}
    assert declared == implemented


# ----- A 方案：前向调用边 vs 失败回退边的区分 -----

def test_split_escalation_targets_separates_forward_and_escalate():
    """前向调用（正文）与失败回退（`## 何时升级`）必须分到两个集合。"""
    from pax.forge.contracts import split_escalation_targets
    body = (
        "## 工作流\n"
        "1. 调用 `pax-gate` 做静态检查\n"
        "## 何时升级\n"
        "- 需要盲审 → `pax-council`\n"
        "- 需要独立验证 → `pax-verify`\n"
    )
    forward, escalate = split_escalation_targets(body, "pax-review")
    assert "pax-gate" in forward
    assert "pax-council" in escalate
    assert "pax-verify" in escalate
    assert "pax-gate" not in escalate


def test_split_escalation_targets_exits_section_at_next_heading():
    """遇到下一个标题即退出升级段落，其后的提及不算回退。"""
    from pax.forge.contracts import split_escalation_targets
    body = (
        "## 何时升级\n"
        "- 失败 → `pax-plan`\n"
        "## 输出契约\n"
        "由编排层调用 `pax-orchestrate` 续接。\n"
    )
    forward, escalate = split_escalation_targets(body, "pax-test")
    assert "pax-plan" in escalate
    assert "pax-orchestrate" in forward
    assert "pax-orchestrate" not in escalate


def test_declared_call_targets_requires_verb_and_backticks():
    """裸提及不算调用声明；必须是动词 + 反引号包裹。"""
    from pax.forge.contracts import _declared_call_targets
    # 有动词 + 反引号 → 是声明
    assert _declared_call_targets("部署前调用 `pax-gate` 做检查") == {"pax-gate"}
    # 只有裸名 → 数据引用，不是调用
    assert _declared_call_targets("读取 pax-plan.rollback_strategy 四档") == set()
    # 有动词但无反引号 → 不认，避免把散文里的举例当调用
    assert _declared_call_targets("调用 pax-gate 或其他") == set()


def test_route_group_needs_two_names():
    """`[x]` 是 checklist 记号，`[clarify, plan]` 才是路由组。"""
    from pax.forge.contracts import split_escalation_targets
    single = "「只写 `[x]` 不算手动证据」\n"
    pair = "路由 `[clarify, plan]` 两步\n"
    f1, _ = split_escalation_targets(single, "pax-execute")
    f2, _ = split_escalation_targets(pair, "pax-orchestrate")
    assert "pax-x" not in f1
    assert "pax-clarify" in f2 and "pax-plan" in f2


def test_extract_escalation_graph_separate_from_call_graph():
    """回退边与前向边必须落在不同的图里，且回退边确实被收集到。"""
    from pax.forge.contracts import _extract_call_graph, _extract_escalation_graph
    import json

    root = Path(__file__).resolve().parents[1]
    if not (root / "pax-ops" / "registry.json").exists():
        pytest.skip("不是家族仓库，跳过")

    forward = _extract_call_graph(root)
    escalate = _extract_escalation_graph(root)

    # pax-test 覆盖率不达标退回 pax-plan 是回退，不该出现在前向图里
    assert "pax-plan" in escalate.get("pax-test", set())
    assert "pax-plan" not in forward.get("pax-test", set())
    # pax-plan 冻结时插入 pax-test 是前向调用
    assert "pax-test" in forward.get("pax-plan", set())