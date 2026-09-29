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


def test_generate_l0_skill(tmp_path):
    skill_dir = generate_skill(
        name="pax-orchestrate", layer="L0",
        description="路由、风险分级、生命周期管理",
        target_root=tmp_path, optional=False,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "## 风险评分维度" in text
    assert "## 路由规则" in text
    assert "## Execution Contract" in text


def test_generate_l2_skill(tmp_path):
    skill_dir = generate_skill(
        name="pax-advisor", layer="L2",
        description="只读顾问",
        target_root=tmp_path, optional=True,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "只读" in text
    assert "不修改快照" in text


def test_generate_l3_skill(tmp_path):
    skill_dir = generate_skill(
        name="pax-worker-grok", layer="L3",
        description="Grok 有界任务执行",
        target_root=tmp_path, optional=True,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "沙箱" in text
    assert "无头执行" in text


def test_generate_l4_skill(tmp_path):
    skill_dir = generate_skill(
        name="pax-verify", layer="L4",
        description="运行中验证",
        target_root=tmp_path, optional=True,
    )
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "五态" in text or "pass" in text
    assert "不认领路由落点" in text
