#!/usr/bin/env python3
"""pax-orchestrate 内部路由评估脚本

测试 pax-orchestrate 的意图分类、风险评分、路由构建准确性。
这是一个框架脚本，实际测试需要运行完整的 pax-orchestrate pipeline。
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TestCase:
    id: str
    category: str
    prompt: str
    expected: dict

@dataclass
class TestResult:
    case_id: str
    category: str
    passed: bool
    expected: dict
    actual: dict
    details: str = ""

def load_dataset(path: str) -> list[TestCase]:
    """加载测试数据集"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cases = []
    for case in data['cases']:
        cases.append(TestCase(
            id=case['id'],
            category=case['category'],
            prompt=case['prompt'],
            expected=case['expected']
        ))
    
    return cases

def evaluate_intent_classification(case: TestCase) -> TestResult:
    """评估意图分类准确性
    
    实际实现需要调用 pax-orchestrate 的意图分类功能。
    这里只是一个框架。
    """
    # 实际实现：
    # 1. 调用 pax-orchestrate 处理 case.prompt
    # 2. 提取意图分类结果
    # 3. 与 expected 比较
    
    # 占位实现：假设返回空结果
    actual = {
        "primary_intent": None,
        "secondary_intent": [],
        "confidence": None
    }
    
    # 比较
    passed = (
        actual['primary_intent'] == case.expected['primary_intent'] and
        set(actual['secondary_intent']) == set(case.expected['secondary_intent']) and
        actual['confidence'] == case.expected['confidence']
    )
    
    return TestResult(
        case_id=case.id,
        category=case.category,
        passed=passed,
        expected=case.expected,
        actual=actual,
        details="框架脚本，未实际调用 pax-orchestrate"
    )

def evaluate_risk_scoring(case: TestCase) -> TestResult:
    """评估风险评分准确性
    
    实际实现需要调用 pax-orchestrate 的风险评分功能。
    这里只是一个框架。
    """
    # 占位实现
    actual = {
        "risk_score": 0,
        "risk_level": "unknown",
        "irreversibility": 0,
        "impact_scope": 0,
        "uncertainty": 0,
        "coordination_cost": 0
    }
    
    # 比较（允许 ±1 分的误差）
    passed = (
        abs(actual['risk_score'] - case.expected['risk_score']) <= 1 and
        actual['risk_level'] == case.expected['risk_level']
    )
    
    return TestResult(
        case_id=case.id,
        category=case.category,
        passed=passed,
        expected=case.expected,
        actual=actual,
        details="框架脚本，未实际调用 pax-orchestrate"
    )

def evaluate_route_building(case: TestCase) -> TestResult:
    """评估路由构建准确性
    
    实际实现需要调用 pax-orchestrate 的路由构建功能。
    这里只是一个框架。
    """
    # 占位实现
    actual = {
        "route": [],
        "diagnose_required": False,
        "storage_backend_required": False
    }
    
    # 比较
    passed = (
        set(actual['route']) == set(case.expected['route']) and
        actual['diagnose_required'] == case.expected['diagnose_required'] and
        actual['storage_backend_required'] == case.expected.get('storage_backend_required', False)
    )
    
    return TestResult(
        case_id=case.id,
        category=case.category,
        passed=passed,
        expected=case.expected,
        actual=actual,
        details="框架脚本，未实际调用 pax-orchestrate"
    )

def main():
    dataset_path = "evals/datasets/pax_internal_routing_v1.0.json"
    
    if not Path(dataset_path).exists():
        print(f"错误：数据集文件不存在：{dataset_path}")
        sys.exit(1)
    
    # 加载数据集
    cases = load_dataset(dataset_path)
    print(f"加载 {len(cases)} 个测试用例")
    
    # 按类别分组
    categories = {}
    for case in cases:
        categories.setdefault(case.category, []).append(case)
    
    print(f"类别分布：")
    for cat, cat_cases in categories.items():
        print(f"  {cat}: {len(cat_cases)} 个用例")
    
    # 运行测试（框架模式）
    results = []
    for case in cases:
        if case.category == "intent_classification":
            result = evaluate_intent_classification(case)
        elif case.category == "risk_scoring":
            result = evaluate_risk_scoring(case)
        elif case.category == "route_building":
            result = evaluate_route_building(case)
        else:
            result = TestResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                expected=case.expected,
                actual={},
                details=f"未知类别：{case.category}"
            )
        results.append(result)
    
    # 统计结果
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    accuracy = passed_count / total_count * 100 if total_count > 0 else 0
    
    print(f"\n测试结果：")
    print(f"  通过：{passed_count}/{total_count} ({accuracy:.1f}%)")
    print(f"  失败：{total_count - passed_count}/{total_count}")
    
    # 按类别统计
    print(f"\n按类别统计：")
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        cat_passed = sum(1 for r in cat_results if r.passed)
        cat_accuracy = cat_passed / len(cat_results) * 100 if cat_results else 0
        print(f"  {cat}: {cat_passed}/{len(cat_results)} ({cat_accuracy:.1f}%)")
    
    # 显示失败案例
    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\n失败案例：")
        for r in failures:
            print(f"  [FAIL] {r.case_id}: {r.details}")
    
    # 保存结果
    output_path = Path("evals/results/internal_routing_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    results_data = {
        "summary": {
            "total": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "accuracy": accuracy
        },
        "by_category": {
            cat: {
                "total": len([r for r in results if r.category == cat]),
                "passed": len([r for r in results if r.category == cat and r.passed])
            }
            for cat in categories
        },
        "results": [
            {
                "case_id": r.case_id,
                "category": r.category,
                "passed": r.passed,
                "details": r.details
            }
            for r in results
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存至：{output_path}")
    
    # 返回退出码
    sys.exit(0 if accuracy >= 80 else 1)

if __name__ == "__main__":
    main()
