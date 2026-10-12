#!/usr/bin/env python3
"""Mutation test: prove run_design_eval.py's scorer actually has teeth.

A scorer that always returns True would "pass" every gate. This injects known
wrong answers and asserts the scorer rejects them. Read-only, no model calls.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "rde", ROOT / "evals" / "run_design_eval.py")
rde = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rde)

ds = json.loads((ROOT / "evals" / "datasets" / "pax-design_v1.0.0.json").read_text(encoding="utf-8"))
cases = {c["id"]: c for c in ds["cases"]}

MUTANTS = [
    # (case_id, mutated_answer, description)
    ("pax-design-dr-01", {"design_required": False, "skip_reason": "no_new_contract_no_boundary_change"},
     "把「必须设计」判成跳过"),
    ("pax-design-dr-02", {"design_required": True, "skip_reason": None},
     "把「无需设计」判成必须设计"),
    ("pax-design-dr-02", {"design_required": False, "skip_reason": "doc_consult_only"},
     "skip_reason 选错枚举值"),
    ("pax-design-dr-03", {"design_required": True, "skip_reason": None},
     "根因已知仍判要设计"),
    ("pax-design-depth-03", {"depth": "minimal"}, "跨服务选型判成 minimal"),
    ("pax-design-depth-02", {"depth": "full"}, "单接口判成 full"),
    ("pax-design-cand-01", {"min_candidates": 1}, "三候选只给 1 个"),
    ("pax-design-cand-02", {"min_candidates": 2}, "无决策场景凭空造候选"),
    ("pax-design-freeze-01", {"status": "frozen"}, "契约不全却冻结"),
]

print("=" * 68)
print("MUTATION TEST — 打乱答案必须被 scorer 判错")
print("=" * 68)
survived = []
for cid, wrong, desc in MUTANTS:
    checks = rde.score_case(cases[cid], wrong)
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
    ({"design_required": False, "skip_reason": None}, "false 但无 skip_reason"),
    ({"design_required": True, "skip_reason": "doc_consult_only"}, "true 却带 skip_reason"),
    ({"design_required": False, "depth": "full"}, "跳过设计却给 full"),
    ({"design_required": True, "depth": "full", "status": "frozen", "min_candidates": 1},
     "full 冻结但候选 < 2"),
]
for obj, desc in struct_cases:
    fails = rde.structure_failures(obj)
    mark = "killed " if fails else "SURVIVED"
    if not fails:
        survived.append(("structure", desc))
    print(f"  [{mark}] {desc}")

print()
if survived:
    print(f"RESULT: {len(survived)} 个变异体存活 —— scorer 无效")
    sys.exit(1)
print(f"RESULT: 全部 {len(MUTANTS) + len(struct_cases)} 个变异体被杀死 —— scorer 有效")