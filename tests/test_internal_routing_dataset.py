"""内部路由数据集结构校验器测试（对应 CI job: internal-routing-check）。

这组测试替代原先 CI 里那段内联 `python -c "..."`：它写死了旧结构
（`data['categories']`）且因双引号转义难以维护，导致该 job 在 workflow
恢复合法后第一次真实运行就 `KeyError: 'categories'`。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_internal_routing.py"
DATASET_PATH = REPO_ROOT / "evals" / "datasets" / "pax_internal_routing_v1.0.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_internal_routing", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def validator():
    return _load_validator()


def _case(**overrides):
    case = {
        "id": "case-1",
        "category": "intent_classification",
        "prompt": "示例输入",
        "expected": {"primary_intent": "feature_dev"},
    }
    case.update(overrides)
    return case


def test_real_dataset_is_structurally_valid(validator):
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    assert validator.validate(data) == []


def test_real_dataset_covers_all_known_categories(validator):
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    seen = {c["category"] for c in data["cases"]}
    assert seen == set(validator.KNOWN_CATEGORIES)


def test_main_exits_zero_on_real_dataset(validator, capsys):
    assert validator.main([str(DATASET_PATH)]) == 0
    assert "Total: 44 cases" in capsys.readouterr().out


def test_main_exits_two_on_missing_file(validator, tmp_path, capsys):
    assert validator.main([str(tmp_path / "nope.json")]) == 2
    assert "数据集不存在" in capsys.readouterr().err


def test_missing_version_and_empty_cases(validator):
    assert "version" in " ".join(validator.validate({"cases": [_case()]}))
    assert "cases" in " ".join(validator.validate({"version": "1.7", "cases": []}))


def test_duplicate_id_is_rejected(validator):
    violations = validator.validate(
        {"version": "1.7", "cases": [_case(), _case()]}
    )
    assert any("重复" in v for v in violations)


def test_unknown_category_is_rejected(validator):
    violations = validator.validate({
        "version": "1.7",
        "cases": [_case(category="whatever")],
    })
    assert any("未知 `category`" in v for v in violations)


def test_missing_expected_keys_per_category(validator):
    violations = validator.validate({
        "version": "1.7",
        "cases": [
            _case(expected={}),                              # 非空对象要求
            _case(id="case-2", category="risk_scoring", expected={"risk_score": 5}),
            _case(id="case-3", category="cross_repo_detection",
                  expected={"cross_repo": True}),
        ],
    })
    joined = " ".join(violations)
    assert "`expected` 必须是非空对象" in joined
    assert "缺少 `risk_level`" in joined
    assert "缺少 `execution_strategy_required`" in joined


def test_valid_case_for_every_category_passes(validator):
    cases = [
        _case(),
        _case(id="c2", category="risk_scoring", expected={
            "risk_score": 10, "risk_level": "high", "irreversibility": 3,
            "impact_scope": 3, "uncertainty": 2, "coordination_cost": 2}),
        _case(id="c3", category="route_building", expected={
            "route": ["clarify"], "diagnose_required": False}),
        _case(id="c4", category="cross_repo_detection", expected={
            "cross_repo": True, "execution_strategy_required": True}),
    ]
    assert validator.validate({"version": "1.7", "cases": cases}) == []


def test_blank_prompt_is_rejected(validator):
    violations = validator.validate(
        {"version": "1.7", "cases": [_case(prompt="   ")]}
    )
    assert any("`prompt` 为空" in v for v in violations)
