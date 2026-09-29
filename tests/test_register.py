"""Tests for register_skill: append, dedupe, sort by created_at."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pax.forge.register import AlreadyRegisteredError, register_skill


def _write_registry(tmp_path: Path, skills: list[dict]) -> Path:
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(
        json.dumps({"family": "pax", "updated_at": None, "skills": skills}),
        encoding="utf-8",
    )
    return reg_path


def test_register_appends(tmp_path, monkeypatch):
    from pax.forge import loader
    reg_path = _write_registry(tmp_path, [])
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)

    entry = {
        "name": "pax-foo", "layer": "L1", "optional": False,
        "version": "0.1.0", "path": "skills/pax-foo/SKILL.md",
        "registered_at": "2026-09-29T00:00:00Z",
    }
    register_skill(entry)
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    assert data["skills"] == [entry]
    assert data["updated_at"] == entry["registered_at"]


def test_register_duplicate_raises(tmp_path, monkeypatch):
    from pax.forge import loader
    existing = [
        {"name": "pax-foo", "path": "x", "version": "0.1.0",
         "layer": "L1", "optional": False,
         "registered_at": "2026-09-29T00:00:00Z"},
    ]
    reg_path = _write_registry(tmp_path, existing)
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)
    with pytest.raises(AlreadyRegisteredError):
        register_skill({
            "name": "pax-foo", "path": "y", "version": "0.1.0",
            "layer": "L1", "optional": False,
            "registered_at": "2026-09-29T00:00:00Z",
        })
    # Registry file must remain unchanged after failure
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    assert data["skills"] == existing


def test_register_sets_registered_at_when_missing(tmp_path, monkeypatch):
    from pax.forge import loader
    reg_path = _write_registry(tmp_path, [])
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)
    register_skill({
        "name": "pax-foo", "layer": "L1", "optional": False,
        "version": "0.1.0", "path": "skills/pax-foo/SKILL.md",
    })
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    assert "registered_at" in data["skills"][0]
    assert data["updated_at"] == data["skills"][0]["registered_at"]


def test_register_requires_name(tmp_path, monkeypatch):
    from pax.forge import loader
    reg_path = _write_registry(tmp_path, [])
    monkeypatch.setattr(loader, "REGISTRY_PATH", reg_path)
    with pytest.raises(ValueError):
        register_skill({"layer": "L1"})
