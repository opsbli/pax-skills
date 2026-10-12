#!/usr/bin/env python3
"""pax-design 评估 runner：真实调用模型，不 mock、不桩。

被测对象是 skills/pax-design/SKILL.md 的 D1（设计必要性）/ D2（设计深度）/
D3（候选充分性）/ D8（冻结门禁）契约。评估器直接抽取 SKILL.md 原文当系统提示
——**不注入 SKILL.md 之外的任何澄清**，否则衡量的是补丁而不是 skill 本身。

用法：
    python evals/run_design_eval.py --dry-run    # 只打印将发送的提示，不调 API
    python evals/run_design_eval.py --repeats 3  # 真实运行（15 题 × 3 = 45 次请求）
    python evals/run_design_eval.py --rescore    # 不调 API，按当前 gold 重判已有结果
    python evals/run_design_eval.py --selfcheck  # 数据集自洽性检查（不调 API、不需密钥）

密钥与端点从环境变量取（DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL）；不在本文件存值。
    python -m pip install openai

两个通过率同时汇报：
  summary          — 原始，包含所有检查项
  summary_adjusted — 剔除 GOLD_CONTRACT_UNDEFINED 里的字段
后者才是模型的真实表现；前者被 gold/契约不一致污染，不可单独引用。
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
SKILL_MD = ROOT / "skills" / "pax-design" / "SKILL.md"
SCHEMA = ROOT / "schemas" / "snapshot.schema.json"
DATASET = ROOT / "evals" / "datasets" / "pax-design_v1.0.0.json"
OUT = ROOT / "evals" / "results" / "design_results.json"

MODEL = os.environ.get("DESIGN_EVAL_MODEL", "deepseek-flash")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 契约边界：D1–D3 + D8。D4–D7 产出为自由文本，不做逐字判定。
CONTRACT_START = "### D1 设计必要性判定"
CONTRACT_STOP = "## 输出契约"

# 门槛按契约确定性分档，不是从测量分布反推：
# D1/D2 是查表 + 布尔判定，应近乎全对；D3 计数判定留一档余量。
GATE_CHECKS = {
    "design_required": 0.95,
    "skip_reason": 0.90,
    "depth": 0.90,
    "min_candidates": 0.85,
    "status": 0.85,
}
GATE_CATEGORY = {
    "design_required": 0.95,
    "design_depth": 0.90,
    "candidate_sufficiency": 0.85,
    "freeze_gate": 0.85,
}
GATE_OVERALL = 0.90
GATE_VALID_RATE = 0.95

# gold 要求但契约未定义的字段——剔除后才反映真实能力。
GOLD_CONTRACT_UNDEFINED: set[tuple[str, str]] = set()

SYSTEM_TAIL = """
请只输出一个 JSON 对象，不要输出任何解释文字或 markdown 代码块。格式：
{
  "design_required": true 或 false,
  "skip_reason": "字符串或 null",
  "depth": "minimal" 或 "standard" 或 "full",
  "min_candidates": 整数（high/standard 深度的高风险决策至少 2；明显无需决策时为 0）,
  "status": "draft" 或 "frozen" 或 "blocked",
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
        "你是 pax-family 的设计门禁 Skill pax-design。严格遵守下面给你的工作流契约，"
        "不要引入契约之外的规则，也不要替用户补充他没有说明的信息。\n"
        + SYSTEM_TAIL
        + "\n\n---\n\n# pax-design 工作流契约\n\n"
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


def structure_failures(obj: dict) -> list[str]:
    """JSON 合法但自相矛盾——属输出健壮性，不算设计判断能力。"""
    fails = []
    dr = obj.get("design_required")
    sr = obj.get("skip_reason")
    if dr is False and not sr:
        fails.append("design_required=false 但 skip_reason 为空")
    if dr is True and sr:
        fails.append("design_required=true 但填了 skip_reason")
    if dr is False and obj.get("depth") == "full":
        fails.append("跳过设计却给出 full 深度")
    st = obj.get("status")
    if st == "frozen" and obj.get("depth") == "full" and not obj.get("min_candidates", 0) >= 2:
        fails.append("full 深度冻结但候选数 < 2")
    return fails


def score_case(case: dict, obj: dict) -> dict:
    exp = case["expected"]
    checks = {}
    for key, want in exp.items():
        if (case["id"], key) in GOLD_CONTRACT_UNDEFINED:
            continue
        got = obj.get(key)
        if key == "min_candidates":
            got_num = got if isinstance(got, int) else -1
            checks[key] = got_num >= want if want > 0 else got_num == 0
        else:
            checks[key] = got == want
    return checks


def selfcheck() -> int:
    """数据集自洽性：gold 字段必须在契约可推导范围内，且不得为空壳。"""
    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    contract = extract_contract()
    problems = []
    ids = [c["id"] for c in ds["cases"]]
    if len(ids) != len(set(ids)):
        problems.append("存在重复 case id")
    for c in ds["cases"]:
        if c["status"] == "TODO" if "status" in c else False:
            problems.append(f"{c['id']}: 仍是 TODO 占位")
        if not c.get("expected"):
            problems.append(f"{c['id']}: expected 为空")
        if "TODO" in json.dumps(c, ensure_ascii=False):
            problems.append(f"{c['id']}: 含 TODO 文本")
    # design_required=false 的题必须带契约里出现过的 skip_reason 值
    valid_skips = {"doc_consult_only", "root_cause_known_single_solution",
                   "no_new_contract_no_boundary_change", "user_explicit_skip"}
    for c in ds["cases"]:
        e = c["expected"]
        if e.get("design_required") is False:
            sr = e.get("skip_reason")
            if sr not in valid_skips:
                problems.append(f"{c['id']}: skip_reason {sr!r} 不在契约允许值内")
        if e.get("design_required") is True and e.get("skip_reason") is not None:
            problems.append(f"{c['id']}: design_required=true 不应带 skip_reason")
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
                     "contract_chars": len(contract),
                     "ran_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()},
            "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = summarize(rows)

    ok, fails = verdict(summary)
    print("\n" + "=" * 60)
    print(f"pax-design 评估 | n={summary['n_judgements']} "
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