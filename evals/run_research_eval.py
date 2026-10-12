#!/usr/bin/env python3
"""pax-research 评估 runner：真实调用模型，不 mock、不桩。

被测对象是 skills/pax-research/SKILL.md 的 R1（只读边界）/ R2（问题拆解）/
R3（多源采集与可信度）/ R4（候选组织，不裁决）/ R5（交接）契约。评估器直接抽取
SKILL.md 原文当系统提示——**不注入 SKILL.md 之外的任何澄清**。

用法：
    python evals/run_research_eval.py --dry-run       # 只打印将发送的提示，不调 API
    python evals/run_research_eval.py --repeats 3     # 真实运行（12 题 × 3 = 36 次请求）
    python evals/run_research_eval.py --rescore       # 不调 API，按当前 gold 重判已有结果
    python evals/run_research_eval.py --selfcheck     # 数据集自洽性检查（不调 API）

密钥与端点从环境变量取（DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL）；不在本文件存值。
    python -m pip install openai
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
SKILL_MD = ROOT / "skills" / "pax-research" / "SKILL.md"
DATASET = ROOT / "evals" / "datasets" / "pax-research_v1.0.0.json"
OUT = ROOT / "evals" / "results" / "research_results.json"

MODEL = os.environ.get("RESEARCH_EVAL_MODEL", "deepseek-flash")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 契约边界：R1–R5 中可机械判定的判据。输出契约里的自由文本段（sources/findings/
# competitors/alternatives 正文）不做逐字判定，只判结构与布尔判据。
CONTRACT_START = "### R1 研究边界与只读确认"
CONTRACT_STOP = "## 输出契约"

# 门槛按契约确定性分档：
# research_required / verdict_locked / read_only 是布尔判据，应近乎全对；
# min_alternatives / has_sources 涉及对象构造，留一档余量。
GATE_CHECKS = {
    "research_required": 0.95,
    "skip_reason": 0.90,
    "read_only": 0.95,
    "min_alternatives": 0.85,
    "verdict_locked": 0.95,
    "has_sources": 0.85,
}
GATE_CATEGORY = {
    "research_required": 0.95,
    "candidate_sufficiency": 0.85,
    "not_verdict": 0.90,
    "source_credibility": 0.85,
    "read_only": 0.95,
}
GATE_OVERALL = 0.90
GATE_VALID_RATE = 0.95

VALID_SKIPS = {"low_risk_clear_goal", "user_explicit_skip", "prior_research_exists"}

SYSTEM_TAIL = """
请只输出一个 JSON 对象，不要输出任何解释文字或 markdown 代码块。格式：
{
  "research_required": true 或 false,
  "skip_reason": "字符串或 null",
  "read_only": true（研究阶段恒为 true）,
  "min_alternatives": 整数（技术选型类至少给足候选；纯背景调研无方案时为 0）,
  "verdict_locked": false（研究只出候选，绝不冻结最终结论）,
  "has_sources": true 或 false（有实质研究结论时必须带来源）,
  "recommendation_candidate": "当前证据下的偏好方（候选，不是最终结论）",
  "confidence": "high" 或 "medium" 或 "low",
  "reasoning": "一句话理由"
}
如果输入缺少契约所需的上下文，按契约本身的判定规则做最合理的判断，不要向用户提问。
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
        "你是 pax-family 的开发前研究 Skill pax-research。严格遵守下面给你的工作流契约，"
        "不要引入契约之外的规则，也不要替用户补充他没有说明的信息。研究阶段只做采集→候选，"
        "不做最终裁决。\n"
        + SYSTEM_TAIL
        + "\n\n---\n\n# pax-research 工作流契约\n\n"
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
            time.sleep(2 ** attempt * 2)
    return None, "rate_limit: retries exhausted"


def structure_failures(obj: dict) -> list[str]:
    """JSON 合法但自相矛盾——属输出健壮性，不算研究判断能力。"""
    fails = []
    rr = obj.get("research_required")
    sr = obj.get("skip_reason")
    if rr is False and not sr:
        fails.append("research_required=false 但 skip_reason 为空")
    if rr is True and sr:
        fails.append("research_required=true 却填了 skip_reason")
    if obj.get("read_only") is False:
        fails.append("研究阶段 read_only=false（违反只读契约）")
    if obj.get("verdict_locked") is True:
        fails.append("研究阶段将最终结论锁死（违反 AI 出候选原则）")
    if rr is False and obj.get("min_alternatives", 0) > 0:
        fails.append("跳过研究却给候选数 > 0")
    return fails


def score_case(case: dict, obj: dict) -> dict:
    exp = case["expected"]
    checks = {}
    for key, want in exp.items():
        got = obj.get(key)
        if key == "min_alternatives":
            got_num = got if isinstance(got, int) else -1
            checks[key] = got_num >= want if want > 0 else got_num == 0
        elif key == "has_sources":
            checks[key] = (got is True) if want else (got is not True)
        else:
            checks[key] = got == want
    return checks


def selfcheck() -> int:
    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    contract = extract_contract()
    problems = []
    ids = [c["id"] for c in ds["cases"]]
    if len(ids) != len(set(ids)):
        problems.append("存在重复 case id")
    for c in ds["cases"]:
        if not c.get("expected"):
            problems.append(f"{c['id']}: expected 为空")
        if "TODO" in json.dumps(c, ensure_ascii=False):
            problems.append(f"{c['id']}: 含 TODO 文本")
        e = c["expected"]
        if e.get("research_required") is False:
            sr = e.get("skip_reason")
            if sr not in VALID_SKIPS:
                problems.append(f"{c['id']}: skip_reason {sr!r} 不在合法枚举内")
            if e.get("min_alternatives", 0) > 0:
                problems.append(f"{c['id']}: 不研究却要求 min_alternatives>0")
        if e.get("research_required") is True and e.get("skip_reason") is not None:
            problems.append(f"{c['id']}: research_required=true 不应带 skip_reason")
        if e.get("verdict_locked") is not False:
            problems.append(f"{c['id']}: research 预期不应锁死结论")
        if e.get("read_only") is not True:
            problems.append(f"{c['id']}: research 预期 read_only 应为 true")
    print(f"契约长度: {len(contract)} 字符")
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
    for k, v in summary["checks"].items():
        if k in GATE_CHECKS and v["rate"] < GATE_CHECKS[k]:
            fails.append(f"{k} {v['rate']:.1%} < {GATE_CHECKS[k]:.0%}")
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
                     "contract_chars": len(contract),
                     "ran_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()},
            "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = summarize(rows)

    ok, fails = verdict(summary)
    print("\n" + "=" * 60)
    print(f"pax-research 评估 | n={summary['n_judgements']} "
          f"valid_rate={summary['valid_rate']:.1%} 能力分={summary['overall']:.1%}")
    print("=" * 60)
    for k, v in summary["checks"].items():
        print(f"  {k:20s} {v['pass']:3d}/{v['n']:<3d} {v['rate']:6.1%}  门槛 {GATE_CHECKS.get(k, 0):.0%}")
    for k, v in summary["categories"].items():
        print(f"  [{k}] {v['pass']}/{v['n']} {v['rate']:.1%}")
    print(f"\nGATE: {'PASS' if ok else 'FAIL'}")
    for f in fails:
        print("  -", f)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
