#!/usr/bin/env python3
"""Mutation test: prove run_research_eval.py's scorer actually has teeth.

A scorer that always returns True would "pass" every gate. This injects known
wrong answers and asserts the scorer rejects them. Read-only, no model calls.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "rre", ROOT / "evals" / "run_research_eval.py")
rre = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rre)

ds = json.loads((ROOT / "evals" / "datasets" / "pax-research_v1.0.0.json").read_text(encoding="utf-8"))
cases = {c["id"]: c for c in ds["cases"]}

MUTANTS = [
    # (case_id, mutated_answer, description)
    ("pax-research-rr-01", {"research_required": False, "skip_reason": "low_risk_clear_goal"},
     "把「必须研究」判成跳过"),
    ("pax-research-rr-02", {"research_required": True, "skip_reason": None},
     "把「无需研究」判成必须研究"),
    ("pax-research-rr-02", {"research_required": False, "skip_reason": None},
     "跳过研究却不说明原因"),
    ("pax-research-cand-01", {"min_alternatives": 1}, "三候选只给 1 个"),
    ("pax-research-cand-02", {"min_alternatives": 2}, "纯背景调研却给方案"),
    ("pax-research-verdict-01", {"verdict_locked": True}, "把研究结论锁死"),
    ("pax-research-ro-01", {"read_only": False}, "研究阶段改成写操作"),
    ("pax-research-src-01", {"has_sources": False}, "有实质结论却不给来源"),
    ("pax-research-rr-01", {"verdict_locked": True}, "选型先锁定最终结论"),
]

print("=" * 68)
print("MUTATION TEST — 打乱答案必须被 scorer 判错")
print("=" * 68)
survived = []
for cid, wrong, desc in MUTANTS:
    checks = rre.score_case(cases[cid], wrong)
    caught = not all(checks.values())
    mark = "killed " if caught else "SURVIVED"
    if not caught:
        survived.append((cid, desc))
    print(f"  [{mark}] {cid}: {desc}")
    print(f"           checks={checks}")

# structure gate must also catch self-contradictory output
print()
print("=" * 68)
print("STRUCTURE GATE — 自相矛盾输出必须判为 invalid")
print("=" * 68)
struct_cases = [
    ({"research_required": False, "skip_reason": None}, "false 但无 skip_reason"),
    ({"research_required": True, "verdict_locked": True, "read_only": True}, "锁死最终结论"),
    ({"research_required": True, "read_only": False}, "研究阶段写业务"),
    ({"research_required": False, "min_alternatives": 3, "skip_reason": "low_risk_clear_goal"},
     "跳过研究却给候选数"),
]
for obj, desc in struct_cases:
    fails = rre.structure_failures(obj)
    mark = "killed " if fails else "SURVIVED"
    if not fails:
        survived.append(("structure", desc))
    print(f"  [{mark}] {desc}")

print()
if survived:
    print(f"RESULT: {len(survived)} 个变异体存活 —— scorer 无效")
    sys.exit(1)
print(f"RESULT: 全部 {len(MUTANTS) + len(struct_cases)} 个变异体被杀死 —— scorer 有效")
