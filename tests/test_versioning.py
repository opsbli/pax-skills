"""Tests for versioning helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pax.forge.versioning import (
    VersionError,
    apply_bump,
    bump_version,
    check_registry_versions,
    deprecate_skill,
    list_version,
)


# ----- bump_version -----

def test_bump_patch():
    assert bump_version("0.1.0", "patch") == "0.1.1"


def test_bump_minor():
    assert bump_version("0.1.0", "minor") == "0.2.0"
    assert bump_version("0.1.5", "minor") == "0.2.0"  # patch resets


def test_bump_major():
    assert bump_version("0.1.5", "major") == "1.0.0"
    assert bump_version("2.3.4", "major") == "3.0.0"


def test_bump_invalid():
    with pytest.raises(VersionError):
        bump_version("0.1.0", "release")


def test_bump_invalid_version_string():
    with pytest.raises(VersionError):
        bump_version("0.1", "patch")
    with pytest.raises(VersionError):
        bump_version("a.b.c", "patch")


# ----- apply_bump -----

def _write_versions(tmp_path: Path) -> Path:
    p = tmp_path / "versions.json"
    p.write_text(
        json.dumps({
            "family": "pax",
            "version": "0.1.0",
            "skills": {"pax-a": {"version": "0.1.0"}},
        }),
        encoding="utf-8",
    )
    return p


def test_apply_bump_writes_versions_json_family_only(tmp_path, monkeypatch):
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    new = apply_bump("minor", family_only=True)
    assert new == "0.2.0"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == "0.2.0"
    # family_only should not sync skills
    assert data["skills"]["pax-a"]["version"] == "0.1.0"


def test_apply_bump_syncs_skills(tmp_path, monkeypatch):
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    apply_bump("minor", family_only=False)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == "0.2.0"
    assert data["skills"]["pax-a"]["version"] == "0.2.0"


def test_apply_bump_invalid_raises(tmp_path, monkeypatch):
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    with pytest.raises(VersionError):
        apply_bump("invalid", family_only=False)


# ----- deprecate_skill -----

def test_deprecate_marks_skill(tmp_path, monkeypatch):
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    deprecate_skill("pax-a")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["skills"]["pax-a"]["status"] == "deprecated"
    # Version should be untouched
    assert data["skills"]["pax-a"]["version"] == "0.1.0"


def test_deprecate_unknown_skill_raises(tmp_path, monkeypatch):
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    with pytest.raises(VersionError):
        deprecate_skill("pax-nope")


# ----- list_version -----

def test_list_version_returns_init_version():
    """list_version reads pax.__init__.__version__."""
    from pax import __version__
    assert list_version() == __version__


# ----- check_registry_versions -----

def test_check_registry_versions_clean(tmp_path, monkeypatch):
    """When every SKILL.md version matches versions.json, return []."""
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    d = tmp_path / "skills" / "pax-a"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-a\nversion: 0.1.0\n---\n\n# pax-a\n",
        encoding="utf-8",
    )
    assert check_registry_versions(tmp_path) == []


def test_check_registry_versions_mismatch(tmp_path, monkeypatch):
    """When SKILL.md version differs from versions.json, report mismatch."""
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    d = tmp_path / "skills" / "pax-a"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: pax-a\nversion: 9.9.9\n---\n\n# pax-a\n",
        encoding="utf-8",
    )
    mismatches = check_registry_versions(tmp_path)
    assert len(mismatches) == 1
    assert "pax-a" in mismatches[0]
    assert "9.9.9" in mismatches[0]
    assert "0.1.0" in mismatches[0]


def test_check_registry_versions_empty_skills_dir(tmp_path, monkeypatch):
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    (tmp_path / "skills").mkdir()
    assert check_registry_versions(tmp_path) == []


def test_check_registry_versions_skips_missing_skill_md(tmp_path, monkeypatch):
    """Directories without SKILL.md are silently skipped."""
    from pax.forge import loader
    p = _write_versions(tmp_path)
    monkeypatch.setattr(loader, "VERSIONS_PATH", p)
    (tmp_path / "skills" / "not-a-skill").mkdir(parents=True)
    assert check_registry_versions(tmp_path) == []
