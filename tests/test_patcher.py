"""Unit tests for pax.forge.patcher (declarative patch layer)."""
from pathlib import Path

import json

import pytest

from pax.forge.patcher import PatchError, apply_manifest, apply_patch


def test_apply_replace_idempotent(tmp_path):
    """同一补丁重复执行两次应无副作用。"""
    target = tmp_path / "skills" / "pax-clarify" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("line A\nline B\n", encoding="utf-8")
    # 注意：needle 与 repl 必须互不为子串，否则第二次调用仍会命中
    patch = {
        "target": "skills/pax-clarify/SKILL.md",
        "operation": "replace",
        "needle": "line B\n",
        "repl": "line B-fixed\n",
    }
    applied = apply_patch(patch, family_root=tmp_path)
    assert applied is True
    text = target.read_text(encoding="utf-8")
    assert "line B-fixed" in text and "line B\n" not in text
    # 第二次：needle 已不在，幂等跳过
    applied2 = apply_patch(patch, family_root=tmp_path)
    assert applied2 is False
    text2 = target.read_text(encoding="utf-8")
    assert "line B-fixed" in text2 and "line B\n" not in text2


def test_apply_replace_strict_raises(tmp_path):
    """非幂等模式下 needle 缺失应报错。"""
    target = tmp_path / "skills" / "pax-clarify" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("line A\n", encoding="utf-8")
    patch = {
        "target": "skills/pax-clarify/SKILL.md",
        "operation": "replace",
        "needle": "not-there",
        "repl": "x",
    }
    with pytest.raises(PatchError):
        apply_patch(patch, family_root=tmp_path, idempotent=False)


def test_apply_append_idempotent(tmp_path):
    target = tmp_path / "foo.md"
    target.write_text("body\n", encoding="utf-8")
    patch = {
        "target": "foo.md",
        "operation": "append",
        "repl": "\nextra\n",
    }
    assert apply_patch(patch, family_root=tmp_path) is True
    assert "extra" in target.read_text(encoding="utf-8")
    # 二次调用：已以 repl 结尾，幂等跳过
    assert apply_patch(patch, family_root=tmp_path) is False


def test_apply_remove_idempotent(tmp_path):
    target = tmp_path / "foo.md"
    target.write_text("a X b\n", encoding="utf-8")
    patch = {"target": "foo.md", "operation": "remove", "needle": " X"}
    assert apply_patch(patch, family_root=tmp_path) is True
    assert "X" not in target.read_text(encoding="utf-8")
    # 二次调用：needle 已不在，幂等跳过
    assert apply_patch(patch, family_root=tmp_path) is False


def test_unknown_operation_raises(tmp_path):
    target = tmp_path / "foo.md"
    target.write_text("x\n", encoding="utf-8")
    with pytest.raises(PatchError):
        apply_patch(
            {"target": "foo.md", "operation": "unknown"},
            family_root=tmp_path,
        )


def test_apply_manifest_marks_applied(tmp_path, monkeypatch):
    from pax.forge import loader

    manifest_path = tmp_path / "pax-ops" / "patches" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "patches": [
                    {
                        "id": "p1",
                        "target": "foo.md",
                        "operation": "replace",
                        "needle": "a",
                        "repl": "b",
                    }
                ],
                "applied": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "PATCHES_MANIFEST_PATH", manifest_path)

    (tmp_path / "foo.md").write_text("a\n", encoding="utf-8")

    n1 = apply_manifest(family_root=tmp_path)
    assert n1 == 1
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["applied"] == ["p1"]
    assert "b" in (tmp_path / "foo.md").read_text(encoding="utf-8")

    # 幂等：第二次不重复应用
    n2 = apply_manifest(family_root=tmp_path)
    assert n2 == 0
    # 内容保持不变
    assert "b" in (tmp_path / "foo.md").read_text(encoding="utf-8")
