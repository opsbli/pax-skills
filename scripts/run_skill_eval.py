#!/usr/bin/env python3
"""通用单 skill 评估 runner。

用法：
    python scripts/run_skill_eval.py --skill pax-plan --dataset evals/datasets/pax-plan_v0.1.0.json

评估流程：
1. 加载数据集
2. 对每个 case 调用 pax-orchestrate 路由，获取预期路由
3. 调用目标 skill 执行任务
4. 对比实际结果与 expected
5. 输出报告

当前状态：骨架，待实现具体评估逻辑。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_dataset(path: Path) -> dict:
    """加载评估数据集"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_skill(skill_name: str, dataset: dict) -> dict:
    """评估单个 skill。
    
    TODO: 实现具体评估逻辑
    - 调用 pax-orchestrate 路由
    - 调用目标 skill
    - 对比结果
    """
    results = []
    
    for case in dataset["cases"]:
        result = {
            "id": case["id"],
            "category": case["category"],
            "prompt": case["prompt"],
            "expected": case["expected"],
            "actual": None,
            "passed": False,
            "score": 0.0
        }
        results.append(result)
    
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    score = passed / total if total > 0 else 0.0
    
    return {
        "skill": skill_name,
        "dataset_version": dataset["version"],
        "total": total,
        "passed": passed,
        "score": score,
        "results": results
    }


def print_report(report: dict) -> None:
    """打印评估报告"""
    print(f"\n# {report['skill']} 评估报告")
    print(f"\n- 数据集版本：{report['dataset_version']}")
    print(f"- 总题数：{report['total']}")
    print(f"- 通过：{report['passed']}")
    print(f"- 得分：{report['score']:.1%}")
    
    if report['results']:
        print("\n## 详情")
        for r in report['results']:
            status = "✅" if r['passed'] else "❌"
            print(f"\n{status} {r['id']} ({r['category']})")
            print(f"   得分：{r['score']:.1%}")


def main() -> int:
    parser = argparse.ArgumentParser(description="单 skill 评估 runner")
    parser.add_argument("--skill", required=True, help="Skill 名称，如 pax-plan")
    parser.add_argument("--dataset", required=True, help="数据集路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        print(f"ERROR: 数据集不存在：{dataset_path}", file=sys.stderr)
        return 1
    
    dataset = load_dataset(dataset_path)
    report = evaluate_skill(args.skill, dataset)
    
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())