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
