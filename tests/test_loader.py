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
    from pax.forge.loader import load_versions
    versions = load_versions()
    assert versions["family"] == "pax"
    assert versions["version"] == "0.1.0"
    assert "skills" in versions
    assert "pax-clarify" in versions["skills"]
    assert versions["skills"]["pax-clarify"]["layer"] == "L1"
    assert "compatibility_matrix" in versions
