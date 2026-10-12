#!/usr/bin/env python3
"""pax-gate 门禁段评估 runner：真实调用模型，不 mock、不桩。

被测对象是 skills/pax-gate/SKILL.md 的 G1（检查范围）/ G2（严重度查表）/
G3（fail-closed 可部署判定）契约。评估器直接抽取 SKILL.md 原文当系统提示
——不注入 SKILL.md 之外的任何澄清。

用法：
    python evals/run_gate_eval.py --dry-run    # 只打印将发送的提示，不调 API
    python evals/run_gate_eval.py --repeats 3  # 真实运行（15 题 × 3 = 45 次请求）
    python evals/run_gate_eval.py --rescore    # 不调 API，按当前 gold 重判已有结果
    python evals/run_gate_eval.py --selfcheck  # 数据集自洽性检查（不调 API、不需密钥）

密钥与端点从环境变量取（DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL）；不在本文件存值。
    python -m pip install openai

门槛按契约确定性分档（§4.6 T-2'）：severity/verdict 是查表判定（0.95），
scope 是布尔查表（0.95），可部署性是 fail-closed 判定（0.95）。不从测量分布反推。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "skills" / "pax-gate" / "SKILL.md"
DATASET = ROOT / "evals" / "datasets" / "pax-gate_v1.0.0.json"
OUT = ROOT / "evals" / "results" / "gate_results.json"

MODEL = os.environ.get("GATE_EVAL_MODEL", "deepseek-flash")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 契约边界：G1–G3。G4（印章写入）为机械追加，不做逐字判定。
CONTRACT_START = "### G1 检查范围判定"
CONTRACT_STOP = "## 输出契约"

# 门槛分档（§4.6 T-2'）：按契约确定性，不从分布反推。
GATE_CHECKS = {
    "severity": 0.95,
    "deployable": 0.95,
    "verdict": 0.95,
    "scope": 0.95,
}
GATE_CATEGORY = {
    "security": 0.90,
    "compliance": 0.90,
    "a11y_i18n": 0.90,
    "license": 0.90,
    "mixed": 0.85,
    "scope": 0.90,
}
GATE_OVERALL = 0.90
GATE_VALID_RATE = 0.95

SYSTEM_TAIL = """
请只输出一个 JSON 对象，不要输出任何解释文字或 markdown 代码块。格式：
{
  "scope": {"security": bool, "compliance": bool, "a11y_i18n": bool, "license": bool},
  "severity": "critical" | "high" | "medium" | "low",
  "deployable": true 或 false,
  "verdict": "blocked" | "needs_review" | "verified",
  "blocking": ["security"] 或 [],
  "reasoning": "一句话理由"
}
如果变更不含某类检查，scope 对应项填 false。判定严重度与可部署性时严格按契约查表与
fail-closed 规则（含并列多个检查项时取最高严重度）。不要向用户提问。
"""


def extract_contract() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    if CONTRACT_START not in text or CONTRACT_STOP not in text:
        raise SystemExit(f"SKILL.md 缺少 {CONTRACT_START!r} 或 {CONTRACT_STOP!r}")
    s = text.index(CONTRACT_START)
    e = text.index(CONTRACT_STOP)
    return text[s:e].strip()


def build_messages(contract: str, prompt: str) -> list[dict[str, str]]:
    system = (
        "你是 pax-family 的门禁段 Skill pax-gate。严格遵守下面给你的工作流契约，"
        "不要引入契约之外的规则，也不要替用户补充他没有说明的信息。\n"
        + SYSTEM_TAIL
        + "\n\n---\n\n# pax-gate 工作流契约\n\n"
        + contract
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": prompt}]


def call_model(client, messages) -> tuple[dict | None, str | None]:
    import time
    for attempt in range(6):
        try:
            resp = client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or ""
            try:
                return json.loads(raw), None
            except json.JSONDecodeError as exc:
                return None, f"json_decode: {exc}"
        except Exception as exc:  # noqa: BLE001
            name = type(exc).__name__
            if "429" not in str(exc) and name != "RateLimitError":
                return None, f"{name}: {exc}"
            time.sleep(2 ** attempt * 2)  # 2,4,8,16,32s backoff
    return None, "rate_limit: retries exhausted"


SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def structure_failures(obj: dict) -> list[str]:
    """JSON 合法但自相矛盾——属输出健壮性，不算门禁判断能力。"""
    fails = []
    sev = obj.get("severity")
    dep = obj.get("deployable")
    ver = obj.get("verdict")
    if sev not in SEV_ORDER:
        fails.append(f"severity {sev!r} 取值非法（应为 {list(SEV_ORDER)} 之一）")
    if sev in ("critical", "high") and dep is not False:
        fails.append("critical/high 却未阻断部署（违反 fail-closed）")
    if sev in ("critical", "high") and ver != "blocked":
        fails.append(f"critical/high 却给 verdict={ver}，应为 blocked")
    if dep is False and ver != "blocked":
        fails.append(f"deployable=false 却给 verdict={ver}，应为 blocked")
    if dep is True and ver not in ("verified", "needs_review"):
        fails.append(f"deployable=true 却给 verdict={ver}，应为 verified/needs_review")
    return fails


def score_case(case: dict, obj: dict) -> dict:
    exp = case["expected"]
    checks = {}
    if "severity" in exp:
        checks["severity"] = obj.get("severity") == exp["severity"]
    if "deployable" in exp:
        checks["deployable"] = obj.get("deployable") == exp["deployable"]
    if "verdict" in exp:
        checks["verdict"] = obj.get("verdict") == exp["verdict"]
    if "scope" in exp:
        want_scope = exp["scope"]
        got_scope = obj.get("scope") or {}
        checks["scope"] = all(got_scope.get(k) is want_scope[k] for k in want_scope)
    if "blocking" in exp:
        want_blocks = set(exp["blocking"])
        got_blocks = set(obj.get("blocking") or [])
        # blocking 判据：阻断集合必须恰好命中 gold 中的", "阻断类别（多/少都算错）
        checks["blocking"] = want_blocks == got_blocks
    return checks


def selfcheck() -> int:
    """数据集自洽性：gold 字段必须在契约可推导范围内，且不得为空壳。"""
    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    problems = []
    ids = [c["id"] for c in ds["cases"]]
    if len(ids) != len(set(ids)):
        problems.append("存在重复 case id")
    valid_sev = {"critical", "high", "medium", "low"}
    valid_ver = {"blocked", "needs_review", "verified"}
    for c in ds["cases"]:
        if "TODO" in json.dumps(c, ensure_ascii=False):
            problems.append(f"{c['id']}: 含 TODO 文本")
        e = c["expected"]
        if "severity" in e and e["severity"] not in valid_sev:
            problems.append(f"{c['id']}: severity {e['severity']!r} 非法")
        if "verdict" in e and e["verdict"] not in valid_ver:
            problems.append(f"{c['id']}: verdict {e['verdict']!r} 非法")
        # fail-closed 自洽：critical/high 必须 deployable=false 且 verdict=blocked
        if e.get("severity") in ("critical", "high"):
            if e.get("deployable") is not False or e.get("verdict") != "blocked":
                problems.append(f"{c['id']}: critical/high 未同时给 deployable=false + verdict=blocked")
        if e.get("deployable") is False and e.get("verdict") != "blocked":
            problems.append(f"{c['id']}: deployable=false 但 verdict={e.get('verdict')}")
        if e.get("deployable") is True and e.get("verdict") not in ("verified", "needs_review"):
            problems.append(f"{c['id']}: deployable=true 但 verdict={e.get('verdict')}")
        if "blocking" in e:
            if bool(e["blocking"]) != (e.get("deployable") is False):
                problems.append(f"{c['id']}: blocking 集合与 deployable 不一致")
    print(f"用例数: {len(ds['cases'])}  唯一 id: {len(set(ids))}")
    if problems:
        for p in problems:
            print("  PROBLEM:", p)
        return 1
    print("SELFCHECK: PASS")
    return 0


def summarize(rows: list[dict]) -> dict:
    per_check = defaultdict(lambda: [0, 0])
    per_cat = defaultdict(lambda: [0, 0])
    valid = 0
    for r in rows:
        cat_ok = all(r["checks"].values()) if r["checks"] else False
        if r["valid"]:
            valid += 1
        for k, ok in r["checks"].items():
            per_check[k][1] += 1
            per_check[k][0] += int(ok)
        per_cat[r["category"]][1] += 1
        per_cat[r["category"]][0] += int(cat_ok)
    total = sum(v[1] for v in per_check.values())
    passed = sum(v[0] for v in per_check.values())
    return {
        "n_judgements": len(rows),
        "valid_rate": round(valid / len(rows), 4) if rows else 0.0,
        "checks": {k: {"pass": v[0], "n": v[1], "rate": round(v[0] / v[1], 4)}
                   for k, v in sorted(per_check.items())},
        "categories": {k: {"pass": v[0], "n": v[1], "rate": round(v[0] / v[1], 4)}
                       for k, v in sorted(per_cat.items())},
        "overall": round(passed / total, 4) if total else 0.0,
    }


def verdict(summary: dict) -> tuple[bool, list[str]]:
    fails = []
    if summary["valid_rate"] < GATE_VALID_RATE:
        fails.append(f"valid_rate {summary['valid_rate']:.1%} < {GATE_VALID_RATE:.0%}")
    if summary["overall"] < GATE_OVERALL:
        fails.append(f"overall {summary['overall']:.1%} < {GATE_OVERALL:.0%}")
    for k, rate in ((k, v["rate"]) for k, v in summary["checks"].items()):
        if k in GATE_CHECKS and rate < GATE_CHECKS[k]:
            fails.append(f"{k} {rate:.1%} < {GATE_CHECKS[k]:.0%}")
    for k, v in summary["categories"].items():
        if k in GATE_CATEGORY and v["rate"] < GATE_CATEGORY[k]:
            fails.append(f"category {k} {v['rate']:.1%} < {GATE_CATEGORY[k]:.0%}")
    return (not fails), fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()

    if args.selfcheck:
        return selfcheck()

    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    contract = extract_contract()

    if args.dry_run:
        msgs = build_messages(contract, ds["cases"][0]["prompt"])
        print("=" * 60)
        print("DRY RUN — 将发送的系统提示（未调 API）")
        print("=" * 60)
        print(msgs[0]["content"][:1200])
        print("...")
        print(f"\n[系统提示总长 {len(msgs[0]['content'])} 字符 | "
              f"数据集 {len(ds['cases'])} 题 × {args.repeats} = "
              f"{len(ds['cases']) * args.repeats} 次请求]")
        return 0

    if args.rescore:
        if not OUT.is_file():
            print(f"没有历史结果：{OUT}", file=sys.stderr)
            return 1
        blob = json.loads(OUT.read_text(encoding="utf-8"))
        ds_by_id = {c["id"]: c for c in ds["cases"]}
        rows = []
        for r in blob["results"]:
            case = ds_by_id[r["id"]]
            rows.append({**r, "category": case["category"],
                         "checks": score_case(case, r["parsed"] or {})})
        summary = summarize(rows)
    else:
        try:
            from openai import OpenAI
        except ModuleNotFoundError:
            print("需要 openai：python -m pip install openai（或用 --selfcheck / --dry-run）",
                  file=sys.stderr)
            return 1
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("缺少 DEEPSEEK_API_KEY（或用 --selfcheck / --dry-run）", file=sys.stderr)
            return 1
        client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=API_BASE)
        rows = []
        for case in ds["cases"]:
            for rep in range(args.repeats):
                obj, err = call_model(client, build_messages(contract, case["prompt"]))
                sfails = structure_failures(obj) if obj else []
                rows.append({
                    "id": case["id"], "category": case["category"], "rep": rep + 1,
                    "parsed": obj, "error": err, "structure_failures": sfails,
                    "valid": obj is not None and not sfails,
                    "checks": score_case(case, obj or {}),
                })
                print(f"  {case['id']} r{rep+1}: "
                      f"{'valid' if rows[-1]['valid'] else 'INVALID'} "
                      f"{sum(rows[-1]['checks'].values())}/{len(rows[-1]['checks'])}")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "meta": {"model": MODEL, "base_url": API_BASE, "temperature": 0,
                     "repeats": args.repeats, "dataset_version": ds["version"],
                     "run_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                     "summary": summarize(rows)},
            "results": rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = summarize(rows)
    ok, fails = verdict(summary)
    print("=" * 68)
    print("SUMMARY (row-unweighted)")
    print("=" * 68)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("=" * 68)
    print("RESULT:", "PASS" if ok else "FAIL")
    for f in fails:
        print("  -", f)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
