from pathlib import Path

import pytest
import yaml

from pax.forge.generator import GenerationError, generate_skill


def test_generate_l1_skill(tmp_path):
    skill_dir = generate_skill(
        name="pax-foo", layer="L1",
        description="A test skill",
        target_root=tmp_path, optional=False,
    )
    assert skill_dir.name == "pax-foo"
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---", 2)[1])
    assert fm["name"] == "pax-foo"
    assert fm["layer"] == "L1"
    assert fm["family"] == "pax"
    assert fm["optional"] is False
    assert "version" in fm
    for section in ["Execution Contract", "职责边界", "输入", "工作流",
                    "输出契约", "失败模式", "何时升级"]:
        assert f"## {section}" in text


def test_generate_rejects_bad_name(tmp_path):
    with pytest.raises(GenerationError):
        generate_skill(name="not-pax-foo", layer="L1",
                       description="x", target_root=tmp_path, optional=False)
