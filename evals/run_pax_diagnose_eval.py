#!/usr/bin/env python3
"""pax-diagnose D5 严重度分级评估：真实调用模型，不 mock、不桩。

被测对象是 skills/pax-diagnose/SKILL.md 的 D1（复现）+ D5（严重度收敛）判定。
评估器抽取 SKILL.md 工作流原文当系统提示——**不注入契约之外的任何澄清**。

用法：
    python evals/run_pax_diagnose_eval.py               # 真实运行（6 次请求）
    python evals/run_pax_diagnose_eval.py --dry-run     # 只打印将发送的提示
    python evals/run_pax_diagnose_eval.py --repeats 5   # 测稳定性
    python evals/run_pax_diagnose_eval.py --rescore     # 不重新调用，重算汇总

密钥与端点从环境变量取；pax-skills 无自带 venv，用 skillEval 的：
    PYTHONUTF8=1 ../agent-skills-tooling/skillEval/.venv/Scripts/python.exe evals/run_pax_diagnose_eval.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "skills" / "pax-diagnose" / "SKILL.md"
DATASET = ROOT / "evals" / "datasets" / "pax_diagnose_v1.0.json"
OUT = ROOT / "evals" / "results" / "pax_diagnose_results.json"

MODEL = os.environ.get("DIAG_EVAL_MODEL", "deepseek-flash")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

CONTRACT_START = "## 工作流"
CONTRACT_STOP = "## 输出契约"

# 检查项门槛：按契约确定性分档（与内部路由一致的原则）
GATE_CHECKS = {
    "severity": 0.85,               # 聚合判定
    "core_flow_broken": 0.80,       # 布尔，但需判断"核心流程"
    "affected_users": 0.80,         # 4 值枚举
    "workaround_available": 0.85,   # 布尔，较明确
    "security_relevant": 0.85,      # 布尔，较明确
    "reproduction_status": 0.95,    # 三值枚举，明确
    "storage_backend_required": 0.90,  # 布尔，触发条件明确
}
GATE_OVERALL = 0.90
GATE_VALID_RATE = 0.95
TZ = ZoneInfo("Asia/Shanghai")


def extract_contract() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    if CONTRACT_START not in text or CONTRACT_STOP not in text:
        raise SystemExit(f"SKILL.md 缺少 {CONTRACT_START!r} 或 {CONTRACT_STOP!r}")
    start = text.index(CONTRACT_START)
    stop = text.index(CONTRACT_STOP)
    return text[start:stop].strip()


def build_messages(contract: str, prompt: str) -> list[dict[str, str]]:
    system = (
        "你是 pax-diagnose，负责对故障/缺陷做根因诊断。严格遵守下面给你的工作流契约，"
        "不要引入契约之外的规则，也不要替用户补充他没有说明的信息。\n"
        "根据用户提供的症状描述，按契约的判定规则做出最合理的判断，然后只输出一个 JSON 对象，"
        "不要输出 JSON 以外的任何文字、不要用 markdown 代码块包裹。\n\n"
        f"{contract}\n\n"
        "输出 JSON 结构：\n"
        "{\n"
        '  "reproduction_status": "reproduced | not_reproduced | partial",\n'
        '  "storage_backend_required": true | false,\n'
        '  "severity": "P0 | P1 | P2",\n'
        '  "severity_rationale": {\n'
        '    "core_flow_broken": true | false,\n'
        '    "affected_users": "all | most | some | few",\n'
        '    "workaround_available": true | false,\n'
        '    "security_relevant": true | false\n'
        "  },\n"
        '  "reasoning": "<一句话依据>"\n'
        "}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]


def call_model(messages: list[dict]) -> tuple[str | None, dict, str | None]:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("缺少 openai 包，请用 skillEval 的 venv 运行")
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=API_BASE)
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0,
        )
    except Exception as e:  # noqa: BLE001
        return None, {}, f"API 错误：{e}"
    content = resp.choices[0].message.content or ""
    usage = {
        "input_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "output_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return content, usage, None


def parse_response(raw: str) -> tuple[dict | None, str | None]:
    """从模型输出里抽出 JSON。容忍代码块包裹。"""
    if not raw:
        return None, "空输出"
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```")[1] if "```" in s[3:] else s[3:]
        s = s.removeprefix("json").strip()
    # 找第一个 { 到最后一个 }
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j < i:
        return None, f"没有 JSON 对象：{raw[:120]!r}"
    try:
        data = json.loads(s[i : j + 1])
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError({e})"
    if not isinstance(data, dict):
        return None, "顶层不是对象"
    return data, None


def normalize_actual(data: dict) -> dict:
    """归一化：大小写、布尔字符串、枚举值。"""
    out = {}
    rs = str(data.get("reproduction_status", "")).strip().lower()
    if rs in ("reproduced", "not_reproduced", "partial"):
        out["reproduction_status"] = rs
    sev = str(data.get("severity", "")).strip().upper()
    if sev in ("P0", "P1", "P2"):
        out["severity"] = sev
    rat = data.get("severity_rationale") or {}
    if isinstance(rat, dict):
        for k in ("core_flow_broken", "workaround_available", "security_relevant"):
            v = rat.get(k)
            if isinstance(v, bool):
                out[k] = v
            elif isinstance(v, str) and v.strip().lower() in ("true", "false"):
                out[k] = v.strip().lower() == "true"
        au = str(rat.get("affected_users", "")).strip().lower()
        if au in ("all", "most", "some", "few"):
            out["affected_users"] = au
    sbr = data.get("storage_backend_required")
    if isinstance(sbr, bool):
        out["storage_backend_required"] = sbr
    elif isinstance(sbr, str) and sbr.strip().lower() in ("true", "false"):
        out["storage_backend_required"] = sbr.strip().lower() == "true"
    return out


def grade(actual: dict, expected: dict) -> list[dict]:
    checks = []
    for field in ("severity", "core_flow_broken", "affected_users",
                  "workaround_available", "security_relevant"):
        if field == "severity":
            exp = expected.get("severity")
        elif field in ("core_flow_broken", "affected_users",
                       "workaround_available", "security_relevant"):
            exp = (expected.get("severity_rationale") or {}).get(field)
        else:
            exp = None
        if exp is None:
            continue
        got = actual.get(field)
        checks.append({"check": field, "passed": got == exp, "actual": got, "expected": exp})
    if "reproduction_status" in expected:
        got = actual.get("reproduction_status")
        exp = expected["reproduction_status"]
        checks.append({"check": "reproduction_status", "passed": got == exp,
                       "actual": got, "expected": exp})
    if "storage_backend_required" in expected:
        got = actual.get("storage_backend_required")
        exp = expected["storage_backend_required"]
        checks.append({"check": "storage_backend_required", "passed": got == exp,
                       "actual": got, "expected": exp})
    return checks


def stamp_meta(meta: dict, contract_chars: int | None = None) -> dict:
    if contract_chars is not None:
        meta["contract_chars"] = contract_chars
    return meta


def print_summary(rows: list[dict], dataset: dict) -> dict:
    n_total = len(rows)
    ok = sum(1 for r in rows if r["passed"])
    parsable = [r for r in rows if r["error"] is None]
    ok_parsable = sum(1 for r in parsable if r["passed"])
    valid_rate = len(parsable) / n_total if n_total else 0.0

    print("=" * 72)
    print(f"总计（原始口径）：{ok}/{n_total} ({ok/n_total*100:.1f}%)" if n_total else "无结果")
    print(f"总计（可解析口径，能力分）：{ok_parsable}/{len(parsable)} "
          f"({ok_parsable/len(parsable)*100:.1f}%) ← gate 以此为准" if parsable else "无可解析结果")
    print(f"输出健壮性：valid_rate = {valid_rate*100:.1f}%  "
          f"(无效输出 {n_total-len(parsable)}/{n_total})")
    for r in rows:
        if r["error"]:
            print(f"      - {r['case_id']} r{r['repeat']}: {r['error'][:100]}")

    # 逐检查项
    print("\n逐检查项（可解析口径，通过率 / 门槛）：")
    all_checks = set()
    for r in parsable:
        for c in r["checks"]:
            all_checks.add(c["check"])
    gate_fail = []
    check_rates = {}
    for chk in sorted(all_checks):
        vals = [c for r in parsable for c in r["checks"] if c["check"] == chk]
        if not vals:
            continue
        p = sum(1 for c in vals if c["passed"])
        rate = p / len(vals)
        check_rates[chk] = rate
        thr = GATE_CHECKS.get(chk, 0.85)
        mark = "✓" if rate >= thr else "✗"
        if rate < thr:
            gate_fail.append(chk)
        print(f"  {mark} {chk:22} {rate*100:.1f}% / ≥ {thr*100:.0f}%   (n={len(vals)})")

    overall = ok_parsable / len(parsable) if parsable else 0.0
    gate_ok = (not gate_fail) and overall >= GATE_OVERALL and valid_rate >= GATE_VALID_RATE
    print()
    if gate_ok:
        print(f"GATE PASS —— 能力 {overall*100:.1f}% / ≥{GATE_OVERALL*100:.0f}%  (n={len(parsable)})")
    else:
        print(f"GATE FAIL —— 能力 {overall*100:.1f}% / ≥{GATE_OVERALL*100:.0f}%  (n={len(parsable)})")
        print(f"     健壮性 valid_rate {valid_rate*100:.1f}% / ≥{GATE_VALID_RATE*100:.0f}%  (n={n_total})")
        if gate_fail:
            print(f"  未达标：{', '.join(gate_fail)}")
    return {"overall": overall, "valid_rate": valid_rate, "gate_ok": gate_ok,
            "gate_fail": gate_fail, "check_rates": check_rates}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--dataset", default=str(DATASET))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--rescore", action="store_true")
    args = ap.parse_args()

    contract = extract_contract()
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    cases = dataset["cases"]

    if args.dry_run:
        msgs = build_messages(contract, cases[0]["prompt"])
        print("=" * 72)
        print("系统提示（前 1500 字）")
        print("=" * 72)
        print(msgs[0]["content"][:1500])
        print(f"\n将发起 {len(cases)} × {args.repeats} = {len(cases)*args.repeats} 次请求")
        return

    if args.rescore:
        old = json.loads(Path(args.out).read_text(encoding="utf-8"))
        rows = old["results"]
        cur_chars = len(contract)
        old_chars = old.get("meta", {}).get("contract_chars")
        if not old_chars or old_chars != cur_chars:
            raise SystemExit(
                f"契约已变化（旧 {old_chars} / 新 {cur_chars} 字符），--rescore 不可用，"
                "必须真实调用模型"
            )
        for r in rows:
            r["checks"] = grade(normalize_actual(r.get("actual") or {}), r["expected"])
            r["passed"] = bool(r["checks"]) and all(c["passed"] for c in r["checks"])
            r["failed_checks"] = [c["check"] for c in r["checks"] if not c["passed"]]
        summary = print_summary(rows, dataset)
        payload = {"meta": stamp_meta(old.get("meta", {}), cur_chars), "results": rows,
                   "summary": summary}
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n结果已保存至：{args.out}（--rescore：未调用模型）")
        return

    print(f"数据集：{len(cases)} 案例 | 模型：{MODEL} @ {API_BASE}")
    print(f"契约：{len(contract)} 字符\n")
    rows, total = [], {"input_tokens": 0, "output_tokens": 0}
    for rep in range(args.repeats):
        for c in cases:
            msgs = build_messages(contract, c["prompt"])
            content, usage, err = call_model(msgs)
            total["input_tokens"] += usage.get("input_tokens", 0)
            total["output_tokens"] += usage.get("output_tokens", 0)
            actual, perr = (None, err) if err else parse_response(content or "")
            if content is None:
                perr = err
            norm = normalize_actual(actual) if actual else {}
            checks = grade(norm, c["expected"]) if actual else []
            passed = bool(checks) and all(x["passed"] for x in checks)
            row = {
                "case_id": c["id"], "category": c["category"], "repeat": rep,
                "holdout": c.get("holdout", False), "prompt": c["prompt"],
                "expected": c["expected"], "actual": actual, "normalized": norm,
                "error": perr if actual is None else None,
                "passed": passed,
                "failed_checks": [x["check"] for x in checks if not x["passed"]],
                "checks": checks,
            }
            rows.append(row)
            status = "PASS" if passed else ("ERR " if row["error"] else "FAIL")
            print(f"  [{status}] {c['id']} r{rep}")

    summary = print_summary(rows, dataset)
    payload = {
        "meta": stamp_meta({
            "model": MODEL, "api_base": API_BASE, "dataset": dataset["version"],
            "repeats": args.repeats, "run_at": datetime.now(TZ).isoformat(),
        }, len(contract)),
        "results": rows,
        "summary": summary,
        "usage": total,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已保存至：{args.out}")


if __name__ == "__main__":
    main()
