"""pax-analyze 行为锁定测试。

本文件锁定「分析/调研」类任务的规范走法（doc_consult → pax-analyze）的关键不变量：

1. pax-analyze 的 frontmatter 与身份：L1、optional、requires_snapshot。
2. SKILL.md 具备 schema 要求的全部必需 section，且工作流为只读 A1–A5。
3. doc_consult 路由确实包含 pax-analyze（与 pax-orchestrate 的 W1/W4 一致）。
4. pax-analyze 正文引用的其它 skill 方向在 compatibility_matrix 内合法（L1 → L2/L3/L4）。
5. references/examples.md 存在且包含样例 A（ES 链路溯源）的关键结论，
   并遵循「真实凭据不落盘、一律 <REDACTED>」约定。

这些是行为契约，不是对模型能力的评估。
"""

from pathlib import Path
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "pax-analyze" / "SKILL.md"
EXAMPLES = ROOT / "skills" / "pax-analyze" / "references" / "examples.md"
ORCH = ROOT / "skills" / "pax-orchestrate" / "SKILL.md"
VERSIONS = ROOT / "pax-ops" / "versions.json"


def test_skill_exists_and_has_valid_frontmatter():
    assert SKILL.exists(), "skills/pax-analyze/SKILL.md 不存在"
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---")
    # frontmatter 关键身份字段
    assert "name: pax-analyze" in text
    assert "layer: L1" in text
    assert "optional: true" in text
    assert "requires_snapshot: true" in text
    assert "family: pax" in text


def test_required_sections_present():
    """schema 要求的全部必需 section 必须存在。"""
    text = SKILL.read_text(encoding="utf-8")
    required = [
        "## Execution Contract",
        "## 职责边界",
        "## 输入",
        "## 工作流",
        "## 输出契约",
        "## 失败模式",
        "## 何时升级",
    ]
    for section in required:
        assert section in text, f"缺少必需 section: {section}"


def test_workflow_is_readonly_a1_to_a5():
    """分析走法必须是只读 A1–A5，且明确只读边界。"""
    text = SKILL.read_text(encoding="utf-8")
    for step in ["### A1 只读边界确认", "### A2 子问题拆解",
                 "### A3 证据收集", "### A4 结论合成", "### A5 可选沉淀与回报"]:
        assert step in text, f"缺少工作流步骤: {step}"
    # 只读性
    assert "read_only" in text or "只读" in text
    assert "不修改业务状态" in text or "不修改" in text


def test_output_contract_writes_analysis_section():
    """输出必须落到 snapshot.analysis，且不改动下游段。"""
    text = SKILL.read_text(encoding="utf-8")
    assert "snapshot.analysis" in text
    # pax-analyze 不应声明写入 diagnose/plan/execution/review
    assert "不改动 `snapshot.diagnosis` / `plan` / `execution` / `review`" in text


def test_orchestrate_route_contains_analyze():
    """pax-orchestrate 的 doc_consult 路由必须是 [clarify, analyze]（含 analyze）。"""
    orch = ORCH.read_text(encoding="utf-8")
    # 路由表与 build_route 两处都要体现 analyze
    assert "[clarify, analyze]" in orch
    assert "analysis_optional_docs" in orch


def test_referenced_skills_layers_are_legal():
    """pax-analyze（L1）正文引用的其它 pax-* 方向必须在 compatibility_matrix 内合法。"""
    text = SKILL.read_text(encoding="utf-8")
    versions = json.loads(VERSIONS.read_text(encoding="utf-8"))
    matrix = versions["compatibility_matrix"]           # {from: [to,...]}
    skill_layers = {
        k: v["layer"] for k, v in versions["skills"].items()
    }
    allowed = {(src, tgt) for src, ts in matrix.items() if not src.startswith("_")
               for tgt in ts}

    SELF = "L1"
    import re
    mentioned = set(re.findall(r"pax-([a-z][a-z0-9-]*)", text))
    for name in mentioned:
        if name not in skill_layers:
            continue  # 未登记/非 skill 引用，跳过
        target = skill_layers[name]
        assert (SELF, target) in allowed, (
            f"pax-analyze (L1) references pax-{name} ({target}): forbidden direction"
        )


def test_examples_exists_and_contains_scenario_a():
    assert EXAMPLES.exists(), "references/examples.md 不存在"
    text = EXAMPLES.read_text(encoding="utf-8")
    # 样例 A：数据链路溯源 + 关键结论
    assert "## 样例 A：数据链路溯源" in text
    assert "usage_daily" in text
    assert "写入/消费链路" in text
    # 样例 B：行为解释 + 方案对比
    assert "## 样例 B" in text


def test_examples_redact_credentials():
    """样例必须脱敏真实凭据，不得出现任何明文密码/token 模式。"""
    text = EXAMPLES.read_text(encoding="utf-8")
    # 出现 REDACTED 占位
    assert "<REDACTED>" in text
    # 不允许出现典型的真实凭据特征（示例中的占位 uesr/password 键不在此限）
    forbidden = ["CMP2023", "tiduyun.com"]
    for token in forbidden:
        assert token not in text, f"样例中出现疑似真实凭据残留: {token}"
