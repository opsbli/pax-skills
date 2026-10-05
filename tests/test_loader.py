from pathlib import Path
import pytest


def test_load_family_schema_shape():
    """Loader 返回结构，键齐全。"""
    from pax.forge.loader import load_family_schema
    schema = load_family_schema()
    assert schema["family"] == "pax"
    assert "Pact-based Agreement" in schema["family_expansion"]
    # 家族 schema 版本（与家族版本 versions.json 是两个独立维度）
    assert schema["version"] == 1.1
    for layer in ["meta", "L0", "L1", "L2", "L3", "L4"]:
        assert layer in schema["layers"]
    # meta 是非运行时工具层：从「成员必须存在」校验中豁免
    assert "meta" in schema["non_runtime_layers"]
    # L1 / L4 的枚举必须覆盖全部后加的 skill（曾漂移过，见 layer-membership 契约）
    assert {"monitor", "rollback", "test", "deploy", "learn"} <= set(schema["layers"]["L1"])
    assert "init" in schema["layers"]["L4"]
    for required_key in ["naming", "required_frontmatter", "required_sections",
                         "declared_checks", "snapshot_schema", "version_source"]:
        assert required_key in schema["contracts"]


def test_load_family_schema_missing_raises(tmp_path, monkeypatch):
    from pax.forge.loader import load_family_schema
    monkeypatch.setattr("pax.forge.loader.FAMILY_SCHEMA_PATH",
                        tmp_path / "does-not-exist.yaml")
    with pytest.raises(FileNotFoundError):
        load_family_schema()


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
        "meta": {"version": 2.0, "created_at": "2026-09-29T00:00:00Z",
                 "updated_at": "2026-09-29T00:00:00Z", "skill_lineage": []},
        "goal": {"statement": "test", "success_criteria": []},
        "consensus": {"required_precision": "low", "dimensions": {},
                       "design_tree": [], "gaps_remaining": []},
        "orchestration": {
            "diagnose_required": False, "rationale": "n/a",
            "skip_reason": None, "route": [],
            "question_strategy": "batch",
            "intent": {"primary": "feature_dev", "secondary": [],
                       "classification_rationale": "n/a"},
            "risk": {"irreversibility": 1, "impact_scope": 1,
                     "uncertainty": 1, "coordination_cost": 1,
                     "total": 4, "level": "low",
                     "forced_escalation": False},
            "annotations": {},
        },
    }
    jsonschema.validate(minimal, schema)  # 不抛异常即通过


def test_snapshot_schema_validates_full_instance():
    """pax-* 各阶段实际会写出的完整快照（格式 2.0）必须通过校验。

    这是对「schema 与 skill 实现是否对齐」的整体闸门：
    若某个 skill 又偷偷写了 schema 没定义的字段，这里会先报错。
    """
    import jsonschema
    from pax.forge.loader import load_snapshot_schema
    schema = load_snapshot_schema()
    full = {
        "meta": {"version": 2.0, "created_at": "2026-10-05T00:00:00Z",
                 "updated_at": "2026-10-05T00:00:00Z",
                 "skill_lineage": ["pax-orchestrate", "pax-clarify"]},
        "goal": {"statement": "s", "success_criteria": ["c"]},
        "consensus": {"required_precision": "medium", "dimensions": {},
                      "design_tree": [], "gaps_remaining": [],
                      "settled_at": None},
        "orchestration": {
            "diagnose_required": True, "rationale": "r", "skip_reason": None,
            "route": ["clarify", "diagnose", "plan", "execute", "review"],
            "question_strategy": "batch",
            "intent": {"primary": "diagnose_fix", "secondary": ["ux_error"],
                       "classification_rationale": "r"},
            "risk": {"irreversibility": 1, "impact_scope": 2,
                     "uncertainty": 2, "coordination_cost": 2,
                     "total": 7, "level": "medium",
                     "forced_escalation": False},
            "annotations": {"frontend_involved": True, "cross_repo": False},
        },
        "symptom": {"description": "d", "impact": "i",
                    "reproduction": "r",
                    "first_observed": "2026-10-05T00:00:00Z"},
        "diagnosis": {"status": "settled", "root_cause": {"statement": "rc"}},
        "infrastructure": {"storage_backend": "postgres"},
        "plan": {"id": "P1", "steps": [], "dependencies": [], "evidence": [],
                 "verification_strategy": [], "status": "frozen",
                 "frozen_at": "2026-10-05T00:00:00Z", "frozen_by": "pax-plan",
                 "rollback_strategy": {"on_failure": [], "on_alert": [],
                                       "on_request": [], "default": []}},
        "contract": {"authorization": {}, "constraints": [], "exceptions": [],
                     "assumptions": [], "withdraw": []},
        "execution": {"id": "E1", "mode": "fix", "status": "completed",
                      "completed_at": "2026-10-05T00:00:00Z", "log": [],
                      "deviations": [], "changes": [],
                      "commits": [{"sha": "abc", "step": "S1"}]},
        "review": {"verdict": "pass", "stamp": "seal-1", "rationale": "r",
                   "findings": [], "verification_results": [],
                   "deviations_check": {}, "stamp_check": {},
                   "reviewed_at": "2026-10-05T00:00:00Z",
                   "reviewed_by": "pax-review"},
        "quality": {"verification_seals": [{"result": "pass",
                                              "evidence": []}],
                    "evolution_entries": []},
        "monitoring": {"status": "ok", "logs": [], "alerts_triggered": []},
        "rollback": {"status": "done", "steps": [], "verification": {}},
        "tests": {"status": "pass", "coverage": {}, "failed_tests": []},
        "deployment": {"status": "done", "environment": "staging",
                       "steps": [], "pre_checks": [], "health_checks": []},
        "learning": {"experiences": [], "knowledge_graph": {},
                     "recommendations": []},
    }
    jsonschema.validate(full, schema)


def test_load_versions_shape():
    import re
    from pax.forge.loader import load_versions
    versions = load_versions()
    assert versions["family"] == "pax"
    # Semantic version; must match pax-ops/versions.json on every release.
    assert re.fullmatch(r"\d+\.\d+\.\d+", versions["version"])
    assert "skills" in versions
    assert "pax-clarify" in versions["skills"]
    assert versions["skills"]["pax-clarify"]["layer"] == "L1"
    assert "compatibility_matrix" in versions


def test_load_versions_consistent_with_registry():
    """Every registered skill must exist in versions.json and have the same
    layer + version. This catches the stale-snapshot drift that used to
    hide behind test_load_versions_shape."""
    from pax.forge.loader import load_versions, load_registry
    versions = load_versions()
    registry = load_registry()
    for entry in registry["skills"]:
        name = entry["name"]
        assert name in versions["skills"], (
            f"{name} in registry.json but not in versions.json"
        )
        v = versions["skills"][name]
        assert v["layer"] == entry["layer"], (
            f"{name} layer mismatch: versions={v['layer']} registry={entry['layer']}"
        )
        assert v["version"] == entry["version"], (
            f"{name} version mismatch: versions={v['version']} registry={entry['version']}"
        )


def test_load_registry_shape():
    from pax.forge.loader import load_registry
    registry = load_registry()
    assert registry["family"] == "pax"
    assert isinstance(registry["skills"], list)
    # registry may contain registered skills (Phase 5 onward); only check shape
    for entry in registry["skills"]:
        assert "name" in entry
        assert "layer" in entry
        assert "version" in entry
        assert "path" in entry
        assert "registered_at" in entry
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
