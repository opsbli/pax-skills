#!/usr/bin/env python3
"""Mutation test: prove run_gate_eval.py's scorer actually has teeth.

A scorer that always returns True would "pass" every gate. This injects known
wrong answers (including fail-closed violations) and asserts the scorer rejects
them. Read-only, no model calls.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "rge", ROOT / "evals" / "run_gate_eval.py")
rge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rge)

ds = json.loads((ROOT / "evals" / "datasets" / "pax-gate_v1.0.0.json").read_text(encoding="utf-8"))
cases = {c["id"]: c for c in ds["cases"]}

MUTANTS = [
    # (case_id, mutated_answer, description)
    ("pax-gate-security-01", {"severity": "low", "deployable": True, "verdict": "verified"},
     "把硬编码密钥判成 low 且放行"),
    ("pax-gate-security-02", {"severity": "medium", "deployable": True, "verdict": "needs_review"},
     "公开 CVE(RCE) 判成 medium"),
    ("pax-gate-security-03", {"severity": "high", "deployable": False, "verdict": "blocked"},
     "把 medium 输入校验缺陷拔高成 high"),
    ("pax-gate-compliance-01", {"severity": "low", "deployable": True, "verdict": "verified"},
     "未同意采集 PII 判成 low 并放行"),
    ("pax-gate-a11y-01", {"severity": "medium", "deployable": True, "verdict": "needs_review"},
     "无标签+对比度不达标判成 medium"),
    ("pax-gate-license-01", {"severity": "low", "deployable": True, "verdict": "verified"},
     "AGPL 与专有代码冲突判成 low"),
    ("pax-gate-mixed-01", {"deployable": True, "verdict": "needs_review", "blocking": []},
     "含 critical 密钥却放行部署"),
    ("pax-gate-mixed-02", {"deployable": False, "verdict": "blocked", "blocking": ["security"]},
     "两个 medium 却误判为阻断"),
    ("pax-gate-mixed-03", {"deployable": True, "verdict": "needs_review", "blocking": []},
     "全通过却给 needs_review"),
    ("pax-gate-scope-01", {"scope": {"security": False, "compliance": False, "a11y_i18n": False, "license": False}},
     "带 UI+PII+新依赖却判全不检查"),
    ("pax-gate-scope-02", {"scope": {"security": False, "compliance": True, "a11y_i18n": True, "license": True}},
     "纯计算函数却判四类全查"),
]

print("=" * 68)
print("MUTATION TEST — 打乱答案必须被 scorer 判错")
print("=" * 68)
survived = []
for cid, wrong, desc in MUTANTS:
    checks = rge.score_case(cases[cid], wrong)
    caught = not all(checks.values())
    mark = "killed " if caught else "SURVIVED"
    if not caught:
        survived.append((cid, desc))
    print(f"  [{mark}] {cid}: {desc}")
    print(f"           checks={checks}")

# structure gate must also catch self-contradictory output (fail-closed violations)
print()
print("=" * 68)
print("STRUCTURE GATE — 自相矛盾输出必须判为 invalid")
print("=" * 68)
struct_cases = [
    ({"severity": "critical", "deployable": True, "verdict": "verified"}, "critical 却放行"),
    ({"severity": "high", "deployable": True, "verdict": "needs_review"}, "high 却 deployable=true"),
    ({"severity": "middle", "deployable": None, "verdict": "blocked"}, "severity 取值非法"),
    ({"deployable": False, "verdict": "verified"}, "deployable=false 却 verified"),
    ({"deployable": True, "verdict": "blocked"}, "deployable=true 却 blocked"),
]
struct_survived = []
for obj, desc in struct_cases:
    fails = rge.structure_failures(obj)
    caught = bool(fails)
    mark = "killed " if caught else "SURVIVED"
    if not caught:
        struct_survived.append((obj, desc))
    print(f"  [{mark}] {desc}: {fails or '未被抓出'}")

print("=" * 68)
muts = [m[2] for m in MUTANTS]
if survived or struct_survived:
    print("RESULT: FAIL — 有存活变异体")
    for cid, desc in survived:
        print(f"  survived(mutation): {cid} {desc}")
    for _, desc in struct_survived:
        print(f"  survived(structure): {desc}")
    sys.exit(1)
print(f"RESULT: PASS — 全部 {len(MUTANTS)} 个变异体 + {len(struct_cases)} 个结构用例被杀")
