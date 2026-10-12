#!/usr/bin/env python3
"""Mutation test: prove run_prd_eval.py's scorer actually has teeth.

Injects known wrong answers and asserts the scorer rejects them. Read-only.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "rpe", ROOT / "evals" / "run_prd_eval.py")
rpe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rpe)

ds = json.loads((ROOT / "evals" / "datasets" / "pax-prototype-to-prd_v1.0.0.json").read_text(encoding="utf-8"))
cases = {c["id"]: c for c in ds["cases"]}

MUTANTS = [
    ("pax-prd-req-01", {"prd_required": False, "skip_reason": "doc_consult_only"},
     "把「要生成 PRD」判成跳过"),
    ("pax-prd-req-02", {"prd_required": True, "skip_reason": None},
     "把「纯文档咨询」判成要生成 PRD"),
    ("pax-prd-req-02", {"prd_required": False, "skip_reason": None},
     "跳过却不说明原因"),
    ("pax-prd-ears-02", {"ears_compliant": True, "verdict": "PASS"},
     "非 EARS 自由文本却判合规通过"),
    ("pax-prd-close-01", {"ears_compliant": False, "verdict": "NEEDS_WORK", "blocked_downstream": False},
     "缺必备章节却只 NEEDS_WORK 且放行"),
    ("pax-prd-close-02", {"scope_defined": False, "verdict": "PASS"},
     "范围未定义却 PASS"),
    ("pax-prd-change-02", {"propagated_before_approval": True},
     "未获批准就传播下游"),
    ("pax-prd-change-01", {"change_status": "applied"},
     "未批准却直接 applied"),
    ("pax-prd-change-03", {"change_status": "pending_approval"},
     "已批准却仍 pending"),
]

print("=" * 68)
print("MUTATION TEST — 打乱答案必须被 scorer 判错")
print("=" * 68)
survived = []
for cid, wrong, desc in MUTANTS:
    checks = rpe.score_case(cases[cid], wrong)
    caught = not all(checks.values())
    mark = "killed " if caught else "SURVIVED"
    if not caught:
        survived.append((cid, desc))
    print(f"  [{mark}] {cid}: {desc}")
    print(f"           checks={checks}")

print()
print("=" * 68)
print("STRUCTURE GATE — 自相矛盾输出必须判为 invalid")
print("=" * 68)
struct_cases = [
    ({"prd_required": False, "skip_reason": None}, "false 但无 skip_reason"),
    ({"verdict": "FAIL", "blocked_downstream": False}, "FAIL 却未阻断下游"),
    ({"propagated_before_approval": True}, "未批准传播"),
    ({"verdict": "BOGUS"}, "verdict 非法枚举"),
]
for obj, desc in struct_cases:
    fails = rpe.structure_failures(obj)
    mark = "killed " if fails else "SURVIVED"
    if not fails:
        survived.append(("structure", desc))
    print(f"  [{mark}] {desc}")

print()
if survived:
    print(f"RESULT: {len(survived)} 个变异体存活 —— scorer 无效")
    sys.exit(1)
print(f"RESULT: 全部 {len(MUTANTS) + len(struct_cases)} 个变异体被杀死 —— scorer 有效")
