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
