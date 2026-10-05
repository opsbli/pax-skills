#!/usr/bin/env python3
"""校验内部路由评估数据集的结构契约（CI job: internal-routing-check）。

背景：`evals/datasets/pax_internal_routing_v1.0.json` 的结构随评估迭代演进，
历史上从「按 category 分组」改成过扁平 `cases` 列表。原先 CI 里用一段
`python -c "..."` 内联脚本做校验，既写死了旧结构（`data['categories']`），
又因为双引号内嵌 `\\"` 转义而难以维护。

本脚本只断言**结构契约**，不评估内容质量——内容准确性由
`evals/run_internal_routing_eval.py` 负责。

结构契约（扁平 `cases` 格式）：
  1. 顶层必需 `version`（字符串）与 `cases`（非空列表）
  2. 每条 case 必需 `id` / `category` / `prompt` / `expected`
  3. `id` 全局唯一且非空
  4. `category` 必须属于 KNOWN_CATEGORIES
  5. `expected` 必须包含该 category 的必需键（REQUIRED_EXPECTED_KEYS）

用法：
    python scripts/validate_internal_routing.py [数据集路径]

退出码：0 = 通过；1 = 存在结构违规；2 = 文件不存在或不是合法 JSON。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_DATASET = Path("evals/datasets/pax_internal_routing_v1.0.json")
CASE_REQUIRED_KEYS = ("id", "category", "prompt", "expected")

KNOWN_CATEGORIES = (
    "intent_classification",
    "risk_scoring",
    "route_building",
    "cross_repo_detection",
)

# 每个 category 在 `expected` 里必须出现的键（与数据集实际结构对齐）
REQUIRED_EXPECTED_KEYS: dict[str, tuple[str, ...]] = {
    "intent_classification": ("primary_intent",),
    "risk_scoring": (
        "risk_score", "risk_level", "irreversibility",
        "impact_scope", "uncertainty", "coordination_cost",
    ),
    "route_building": ("route", "diagnose_required"),
    "cross_repo_detection": ("cross_repo", "execution_strategy_required"),
}


def validate(data: object) -> list[str]:
    """返回结构违规列表；空列表表示通过。"""
    violations: list[str] = []
    if not isinstance(data, dict):
        return ["顶层结构必须是 JSON 对象"]

    if not isinstance(data.get("version"), str) or not data.get("version"):
        violations.append("缺少顶层 `version`（字符串）")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        violations.append("缺少顶层 `cases`（非空列表）")
        return violations

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        where = f"cases[{index}]"
        if not isinstance(case, dict):
            violations.append(f"{where}: 必须是 JSON 对象")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            violations.append(f"{where}: 缺少非空字符串 `id`")
        else:
            where = case_id
            if case_id in seen_ids:
                violations.append(f"{case_id}: `id` 重复")
            seen_ids.add(case_id)

        for key in CASE_REQUIRED_KEYS:
            if key not in case:
                violations.append(f"{where}: 缺少字段 `{key}`")

        prompt = case.get("prompt")
        if isinstance(prompt, str) and not prompt.strip():
            violations.append(f"{where}: `prompt` 为空")

        category = case.get("category")
        if category not in KNOWN_CATEGORIES:
            violations.append(
                f"{where}: 未知 `category` {category!r}"
                f"（已知：{', '.join(KNOWN_CATEGORIES)}）"
            )
            continue

        expected = case.get("expected")
        if not isinstance(expected, dict) or not expected:
            violations.append(f"{where}: `expected` 必须是非空对象")
            continue
        for key in REQUIRED_EXPECTED_KEYS[category]:
            if key not in expected:
                violations.append(
                    f"{where}: category={category} 的 `expected` 缺少 `{key}`"
                )

    return violations


def summarize(data: dict) -> None:
    counts: dict[str, int] = {}
    for case in data.get("cases", []):
        if isinstance(case, dict):
            counts[case.get("category", "<无 category>")] = (
                counts.get(case.get("category", "<无 category>"), 0) + 1
            )
    for category in KNOWN_CATEGORIES:
        if category in counts:
            print(f"  {category}: {counts[category]} cases")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else DEFAULT_DATASET

    if not path.is_file():
        print(f"ERROR: 数据集不存在: {path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path} 不是合法 JSON: {exc}", file=sys.stderr)
        return 2

    summarize(data if isinstance(data, dict) else {})
    violations = validate(data)
    if violations:
        print(f"\n共 {len(violations)} 处结构违规：", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    total = len(data.get("cases", [])) if isinstance(data, dict) else 0
    print(f"  Total: {total} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
