"""End-to-end pipeline: init -> new -> validate -> register -> list -> version --list.

Runs entirely inside ``tmp_path`` by redirecting ``pax.forge.loader`` paths,
then captures the ``list`` and ``version --list`` CLI output via
``pax.forge.cli.main``.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from pax.forge import loader


def test_full_pipeline(tmp_path: Path, monkeypatch):
    # 1. init: create the family skeleton in tmp_path/fam
    from pax.forge.init import init_family
    fam = tmp_path / "fam"
    init_family(fam)

    # init_family copies the current registry.json which includes all 13
    # registered skills from Phase 5. Clear it so the e2e test starts
    # from a clean state and only registers pax-foo.
    reg_path = fam / "pax-ops" / "registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["skills"] = []
    reg_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")

    # 2. Redirect loader paths to the tmp family (monkeypatched so they
    # restore automatically after the test finishes).
    monkeypatch.setattr(
        loader, "FAMILY_SCHEMA_PATH",
        fam / "schemas" / "pax-family.schema.yaml",
    )
    monkeypatch.setattr(
        loader, "SNAPSHOT_SCHEMA_PATH",
        fam / "schemas" / "snapshot.schema.json",
    )
    monkeypatch.setattr(
        loader, "VERSIONS_PATH",
        fam / "pax-ops" / "versions.json",
    )
    monkeypatch.setattr(
        loader, "REGISTRY_PATH",
        fam / "pax-ops" / "registry.json",
    )
    monkeypatch.setattr(
        loader, "PATCHES_MANIFEST_PATH",
        fam / "pax-ops" / "patches" / "manifest.json",
    )

    # 3. new: generate a skill
    from pax.forge.generator import generate_skill
    skill_dir = generate_skill(
        name="pax-foo", layer="L1",
        description="A test skill",
        target_root=fam, optional=False,
    )
    assert (skill_dir / "SKILL.md").exists()

    # 4. validate
    from pax.forge.validator import validate_skill
    report = validate_skill(skill_dir)
    assert report.ok, report.violations

    # 5. register
    from pax.forge.register import register_skill
    entry = {
        "name": "pax-foo", "layer": "L1", "optional": False,
        "version": "0.1.0",
        "path": "skills/pax-foo/SKILL.md",
        "registered_at": "2026-09-29T00:00:00Z",
    }
    register_skill(entry)

    # 6. list + version --list via CLI main()
    from pax.forge.cli import main

    # Restore original CWD-independent paths so `main(["list"])` picks
    # up the tmp registry.
    list_buf = io.StringIO()
    with redirect_stdout(list_buf):
        rc = main(["list"])
    assert rc == 0, list_buf.getvalue()
    list_out = list_buf.getvalue()

    ver_buf = io.StringIO()
    with redirect_stdout(ver_buf):
        rc = main(["version", "--list"])
    assert rc == 0, ver_buf.getvalue()
    ver_out = ver_buf.getvalue()

    combined = list_out + ver_out

    # 7. Final assertions
    assert "pax-foo@0.1.0" in list_out
    assert "0.1.0" in ver_out

    # Sanity-check the registry file on disk
    reg = json.loads(
        (fam / "pax-ops" / "registry.json").read_text(encoding="utf-8")
    )
    assert reg["skills"] == [entry]
