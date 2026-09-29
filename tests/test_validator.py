from pathlib import Path

from pax.forge.validator import ValidationReport, validate_skill


BASE_SKILL = (
    "---\n"
    "name: pax-ok\n"
    "description: >\n  A valid skill.\n"
    "version: 0.1.0\n"
    "family: pax\n"
    "layer: L1\n"
    "optional: false\n"
    "requires_snapshot: true\n"
    "---\n\n# pax-ok\n\n"
    "## Execution Contract\n- ...\n\n"
    "## 职责边界\n- ...\n\n"
    "## 输入\n- ...\n\n"
    "## 工作流\n1. ...\n\n"
    "## 输出契约\n- ...\n\n"
    "## 失败模式\n- ...\n\n"
    "## 何时升级\n- ...\n"
)


def _write(tmp_path: Path, name: str, text: str = BASE_SKILL) -> Path:
    d = tmp_path / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    return d


def test_validate_ok(tmp_path):
    d = _write(tmp_path, "pax-ok")
    report = validate_skill(d)
    assert report.ok
    assert report.violations == []


def test_validate_missing_required_section(tmp_path):
    d = _write(tmp_path, "pax-bad")
    text = BASE_SKILL.replace("## 何时升级\n- ...\n", "")
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    report = validate_skill(d)
    assert not report.ok
    assert any("何时升级" in v for v in report.violations)


def test_validate_missing_frontmatter_key(tmp_path):
    d = _write(tmp_path, "pax-nofm")
    text = BASE_SKILL.replace("requires_snapshot: true\n", "")
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    report = validate_skill(d)
    assert not report.ok
    assert any("requires_snapshot" in v for v in report.violations)
