#!/usr/bin/env python3
"""Validate pax-design output against the real snapshot schema.

Positive: a frozen `full`-depth design with ADR + contracts + SLO must validate.
Negative: malformed payloads must be rejected (proves the schema has teeth).

Read-only; no model calls.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
schema = json.loads((ROOT / "schemas" / "snapshot.schema.json").read_text(encoding="utf-8"))
try:
    import jsonschema
except ModuleNotFoundError:
    sys.exit("需要 jsonschema：pip install jsonschema")

BASE = {
    "meta": {"version": 2.0, "created_at": "2026-10-12T00:00:00Z",
             "updated_at": "2026-10-12T00:00:00Z",
             "skill_lineage": ["pax-orchestrate", "pax-clarify", "pax-design"]},
    "goal": {"statement": "新增退款接口", "success_criteria": ["退款可追溯"]},
    "consensus": {"required_precision": "high", "dimensions": {}, "design_tree": [],
                  "gaps_remaining": []},
    "orchestration": {
        "diagnose_required": False, "rationale": "新功能", "skip_reason": "new_feature_no_prior_behavior",
        "route": ["clarify", "design", "plan", "execute", "review"],
        "question_strategy": "one-by-one",
        "intent": {"primary": "feature_dev", "secondary": ["integration"],
                    "classification_rationale": "新增对外接口"},
        "risk": {"irreversibility": 2, "impact_scope": 2, "uncertainty": 2,
                  "coordination_cost": 2, "total": 8, "level": "medium",
                  "forced_escalation": False},
        "annotations": {"integration_contract_required": True},
    },
    "design": {
        "design_required": True,
        "skip_reason": None,
        "depth": "full",
        "candidates": [
            {"id": "C1", "name": "同步补偿", "pros": ["实现简单"], "cons": ["需人工重试"]},
            {"id": "C2", "name": "异步 Saga", "pros": ["自动补偿"], "cons": ["复杂度高"]},
        ],
        "adrs": [{
            "id": "ADR-1", "title": "退款走异步 Saga", "status": "accepted",
            "context": "第三方支付回调不可靠", "decision": "采用异步补偿",
            "alternatives": ["同步补偿：需人工重试"],
            "consequences": {"positive": ["自动补偿"], "negative": ["引入 Saga 复杂度"]},
            "supersedes": None, "decided_at": "2026-10-12T00:00:00Z",
        }],
        "api_contracts": [{
            "name": "POST /refunds", "method": "POST", "path": "/refunds",
            "request": "order_id: string | 必填 | 非空",
            "response": "refund_id: string",
            "error_codes": [{"code": "REFUND_DUPLICATE", "when": "同一订单重复退款"}],
            "auth": "服务间 mTLS", "version": "v1",
        }],
        "data_models": [{
            "name": "Refund",
            "fields": [{"name": "refund_id", "type": "uuid", "constraints": "唯一 非空"}],
            "relationships": ["Order 1:N Refund（order_id 外键）"],
            "indexes": ["按 order_id 查询退款 → idx_refund_order"],
        }],
        "service_boundaries": [{
            "name": "payment", "responsibility": "退款执行与补偿",
            "depends_on": ["order"], "exposes": ["POST /refunds"],
        }],
        "observability_plan": {
            "logs": ["结构化：refund_id/order_id/结果"],
            "metrics": ["refund_failure_total: counter"],
            "traces": ["payment -> order 补偿链路"],
            "slo": [{"metric": "refund_failure_rate", "target": "<0.1%",
                     "alert_threshold": ">1%"}],
        },
        "security_considerations": ["退款接口需鉴权并审计操作人"],
        "review": {"required": True, "verdict": "accepted", "round": 1},
        "open_questions": [],
        "status": "frozen",
        "frozen_at": "2026-10-12T00:00:00Z",
    },
}

validator = jsonschema.Draft202012Validator(schema)
cases = [
    ("positive: full-depth frozen design", BASE, True),
    ("negative: ADR missing required id",
     _mut := (lambda d: (d["design"]["adrs"][0].pop("id"), d)[1])(copy.deepcopy(BASE)), False),
    ("negative: unknown depth enum",
     (lambda d: (d["design"].__setitem__("depth", "partial"), d)[1])(copy.deepcopy(BASE)), False),
    ("negative: typo field sneaks in",
     (lambda d: (d["design"].__setitem__("adr", []), d)[1])(copy.deepcopy(BASE)), False),
    ("negative: design_required as string",
     (lambda d: (d["design"].__setitem__("design_required", "yes"), d)[1])(copy.deepcopy(BASE)), False),
    ("negative: verdict outside enum",
     (lambda d: (d["design"]["review"].__setitem__("verdict", "lgtm"), d)[1])(copy.deepcopy(BASE)), False),
]

print("=" * 66)
print("pax-design 输出契约校验（schema: snapshot.schema.json）")
print("=" * 66)
allok = True
for name, doc, should_pass in cases:
    errs = list(validator.iter_errors(doc))
    accepted = not errs
    ok = accepted == should_pass
    allok &= ok
    mark = "PASS" if ok else "FAIL"
    want = "accepted" if should_pass else "rejected"
    got = "accepted" if accepted else "rejected"
    print(f"  [{mark}] {name}\n         expect={want} got={got}")
    if not ok and errs:
        print("        ", errs[0].message[:120])
print()
print("RESULT:", "all expectations met" if allok else "MISMATCH")
sys.exit(0 if allok else 1)