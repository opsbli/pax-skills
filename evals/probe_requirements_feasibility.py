#!/usr/bin/env python3
"""Probe: would the requirements doc's proposed design survive pax contracts?

Read-only. Simulates (a) snapshot top-level field acceptance,
(b) layer-call legality for proposed layers, (c) call-graph cycles.
"""
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(r"C:/Users/sam/Documents/skills/pax-skills")
sys.path.insert(0, str(ROOT / "src"))
import jsonschema  # noqa: E402

versions = json.loads((ROOT / "pax-ops" / "versions.json").read_text(encoding="utf-8"))
schema = json.loads((ROOT / "schemas" / "snapshot.schema.json").read_text(encoding="utf-8"))
matrix = versions["compatibility_matrix"]

print("=" * 70)
print("A. snapshot top-level field acceptance (additionalProperties=false)")
print("=" * 70)
top = set(schema["properties"])
proposed = [
    "research_snapshot", "design_snapshot", "frontend_design_snapshot",
    "security_snapshot", "migration_snapshot", "a11y_i18n_snapshot",
    "cicd_snapshot", "observability_snapshot", "performance_snapshot",
    "incident_snapshot", "refactor_snapshot", "compliance_snapshot",
    "audit_snapshot", "tech_stack_snapshot",
]
validator = jsonschema.Draft202012Validator(schema)
ok = bad = 0
for name in proposed:
    probe = {
        "meta": {"version": 2.0, "created_at": "2026-10-12T00:00:00Z",
                 "updated_at": "2026-10-12T00:00:00Z", "skill_lineage": ["pax-orchestrate"]},
        "goal": {"statement": "x", "success_criteria": []},
        "consensus": {"required_precision": "low", "dimensions": {},
                      "design_tree": [], "gaps_remaining": []},
        "orchestration": {
            "diagnose_required": False, "rationale": "x", "skip_reason": None,
            "route": ["clarify"], "question_strategy": "batch",
            "intent": {"primary": "doc_consult", "secondary": [],
                       "classification_rationale": "x"},
            "risk": {"irreversibility": 1, "impact_scope": 1, "uncertainty": 1,
                     "coordination_cost": 1, "total": 4, "level": "low",
                     "forced_escalation": False},
            "annotations": {},
        },
        name: {},
    }
    errs = [e.message for e in validator.iter_errors(probe)
            if "Additional properties" in e.message]
    if errs:
        bad += 1
        print(f"  REJECTED  {name}")
    else:
        ok += 1
        print(f"  accepted  {name}")
print(f"\n  => {bad}/{len(proposed)} proposed snapshot types REJECTED by schema")

print()
print("=" * 70)
print("B. layer-call legality for proposed layer assignments")
print("=" * 70)
proposed_layers = {
    "pax-memory": "L0", "pax-auto-research": "L1", "pax-design": "L1",
    "pax-frontend-design": "L1", "pax-design-system-extract": "L2",
    "pax-security": "L4", "pax-db-migration": "L4", "pax-a11y-i18n": "L4",
    "pax-cicd": "L1", "pax-incident": "L4", "pax-refactor": "L1",
    "pax-compliance": "L4", "pax-self-audit": "L4",
    "pax-tech-stack-selector": "L1", "pax-fullstack-builder": "L1",
}
existing = {
    "pax-orchestrate": "L0", "pax-clarify": "L1", "pax-diagnose": "L1",
    "pax-plan": "L1", "pax-execute": "L1", "pax-review": "L1",
    "pax-analyze": "L1", "pax-monitor": "L1", "pax-rollback": "L1",
    "pax-test": "L1", "pax-deploy": "L1", "pax-learn": "L1",
    "pax-advisor": "L2", "pax-council": "L2",
    "pax-worker-research": "L3", "pax-worker-implement": "L3",
    "pax-verify": "L4", "pax-evolve": "L4", "pax-docs": "L4", "pax-init": "L4",
}
all_layers = dict(existing)
all_layers.update(proposed_layers)
allowed = {(s, t) for s, ts in matrix.items()
           if not s.startswith("_") for t in ts}

# dependencies exactly as the requirements doc declares them
deps = {
    "pax-auto-research": ["pax-worker-research", "pax-council", "pax-clarify", "pax-plan"],
    "pax-design": ["pax-auto-research", "pax-council", "pax-review", "pax-frontend-design"],
    "pax-frontend-design": ["pax-design", "pax-design-system-extract", "pax-a11y-i18n"],
    "pax-design-system-extract": ["pax-frontend-design"],
    "pax-security": ["pax-execute", "pax-review", "pax-deploy", "pax-compliance"],
    "pax-db-migration": ["pax-execute", "pax-test", "pax-rollback"],
    "pax-a11y-i18n": ["pax-frontend-design", "pax-review"],
    "pax-cicd": ["pax-deploy"],
    "pax-incident": ["pax-monitor", "pax-diagnose", "pax-learn"],
    "pax-refactor": ["pax-test", "pax-review", "pax-self-audit"],
    "pax-compliance": ["pax-design", "pax-review", "pax-security"],
    "pax-self-audit": ["pax-memory", "pax-orchestrate", "pax-plan", "pax-execute"],
    "pax-tech-stack-selector": ["pax-auto-research"],
    "pax-fullstack-builder": ["pax-tech-stack-selector", "pax-design", "pax-execute", "pax-test"],
    "pax-memory": ["pax-orchestrate"],
}
viol = []
for src, targets in deps.items():
    sl = proposed_layers.get(src) or existing[src]
    for t in targets:
        tl = all_layers.get(t)
        if (sl, tl) not in allowed:
            viol.append((src, sl, t, tl))
print(f"  forbidden-direction edges: {len(viol)}")
for s, sl, t, tl in viol:
    print(f"    {s} ({sl}) -> {t} ({tl})   [matrix allows {sl}->{matrix.get(sl, [])}]")

print()
print("=" * 70)
print("C. call-graph cycles (contract 'no-cycles')")
print("=" * 70)
graph = dict(deps)
cycles = set()
def dfs(n, path):
    if n in path:
        cycles.add(tuple(path[path.index(n):] + [n]))
        return
    for m in graph.get(n, []):
        dfs(m, path + [n])
for n in list(graph):
    dfs(n, [])
if cycles:
    print(f"  cycles found: {len(cycles)}")
    for c in sorted(cycles)[:12]:
        print("    " + " -> ".join(c))
else:
    print("  no cycles")

print()
print("=" * 70)
print("D. L4 outbound edges declared in compatibility_matrix")
print("=" * 70)
for L in ("L0", "L1", "L2", "L3", "L4"):
    print(f"  {L} -> {matrix.get(L, '*** NOT DECLARED (no outbound edges) ***')}")