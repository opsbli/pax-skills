"""End-to-end: apply patches through the manifest and verify idempotent replay.

Differs from ``test_patcher.py`` (unit-level, isolated file I/O) by:
- Using a real family tree under ``tmp_path`` with an actual ``pax-ops/patches/
  manifest.json`` on disk.
- Exercising the loader indirection (``PATCHES_MANIFEST_PATH``) rather than
  constructing patch dicts directly.
- Re-running ``apply_manifest`` and asserting the file content is byte-identical.
"""
from __future__ import annotations

import json

from pax.forge import loader


def test_end_to_end_patch_idempotent(tmp_path, monkeypatch):
    root = tmp_path / "fam"
    (root / "skills").mkdir(parents=True)
    target = root / "skills" / "target.md"
    target.write_text("hello\nworld\n", encoding="utf-8")

    manifest_path = root / "pax-ops" / "patches" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "patches": [
                    {
                        "id": "p1",
                        "target": "skills/target.md",
                        "operation": "replace",
                        "needle": "world",
                        "repl": "PLANET",
                    }
                ],
                "applied": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "PATCHES_MANIFEST_PATH", manifest_path)

    from pax.forge.patcher import apply_manifest

    # First run: one patch applied, target rewritten, manifest persisted.
    n1 = apply_manifest(family_root=root)
    assert n1 == 1
    text = target.read_text(encoding="utf-8")
    assert "PLANET" in text and "world" not in text
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["applied"] == ["p1"]

    # Second run: idempotent — no new patches, target untouched.
    n2 = apply_manifest(family_root=root)
    assert n2 == 0
    assert target.read_text(encoding="utf-8") == text


def test_end_to_end_multiple_operations_in_one_manifest(tmp_path, monkeypatch):
    """replace / append / remove 混合在一个 manifest 里，两次 apply 结果一致。"""
    root = tmp_path / "fam"
    target = root / "target.md"
    root.mkdir(parents=True)
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    manifest_path = root / "pax-ops" / "patches" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "patches": [
                    {
                        "id": "p1",
                        "target": "target.md",
                        "operation": "replace",
                        "needle": "beta",
                        "repl": "BETA",
                    },
                    {
                        "id": "p2",
                        "target": "target.md",
                        "operation": "append",
                        "repl": "\n-- end --\n",
                    },
                    {
                        "id": "p3",
                        "target": "target.md",
                        "operation": "remove",
                        "needle": " gamma",
                    },
                ],
                "applied": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "PATCHES_MANIFEST_PATH", manifest_path)

    from pax.forge.patcher import apply_manifest

    n1 = apply_manifest(family_root=root)
    assert n1 == 3
    text = target.read_text(encoding="utf-8")
    assert "BETA" in text
    assert "-- end --" in text
    assert "gamma" not in text

    n2 = apply_manifest(family_root=root)
    assert n2 == 0
    # 二次运行没有改变文件内容
    assert target.read_text(encoding="utf-8") == text
