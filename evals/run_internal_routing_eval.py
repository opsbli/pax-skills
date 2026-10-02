#!/usr/bin/env python3
"""pax-orchestrate 内部路由评估：真实调用模型，不 mock、不桩。

被测对象是 skills/pax-orchestrate/SKILL.md 的 W1–W4 工作流（意图分类 / 风险评分 /
诊断必要性 / 路由构建）。评估器直接抽取 SKILL.md 原文当系统提示——**不注入 SKILL.md
之外的任何澄清**，否则结果衡量的是我们的补丁而不是这个 skill 本身。

用法：
    python evals/run_internal_routing_eval.py              # 真实运行（14 次请求）
    python evals/run_internal_routing_eval.py --dry-run    # 只打印将发送的提示，不调 API
    python evals/run_internal_routing_eval.py --repeats 3  # 测稳定性/方差
    python evals/run_internal_routing_eval.py --rescore    # 不重新调用，重算已有结果的汇总

密钥与端点从环境变量取（DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL）；不在本文件存值。
pax-skills 自带 venv 没装 openai，用 skillEval 的：
    skillEval/.venv/Scripts/python.exe evals/run_internal_routing_eval.py

两个通过率同时汇报：
  summary            — 原始，包含所有检查项
  summary_adjusted   — 剔除 GOLD_CONTRACT_UNDEFINED 里的字段（gold 要求但契约未定义）
后者才是模型的真实表现；前者被 gold/契约不一致污染，不可单独引用。
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
SKILL_MD = ROOT / "skills" / "pax-orchestrate" / "SKILL.md"
DATASET = ROOT / "evals" / "datasets" / "pax_internal_routing_v1.0.json"
OUT = ROOT / "evals" / "results" / "internal_routing_results.json"

MODEL = os.environ.get("INTERNAL_EVAL_MODEL", "deepseek-flash")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 契约边界：W1 意图分类 → W4 路由构建。W5 快照初始化不参与本评估。
CONTRACT_START = "### W1 意图分类"
CONTRACT_STOP = "### W5 快照初始化"


def extract_contract() -> str:
    """从 SKILL.md 抽取 W1–W4 原文作为系统提示主体。"""
    text = SKILL_MD.read_text(encoding="utf-8")
    if CONTRACT_START not in text or CONTRACT_STOP not in text:
        raise SystemExit(f"SKILL.md 缺少 {CONTRACT_START!r} 或 {CONTRACT_STOP!r}")
    start = text.index(CONTRACT_START)
    stop = text.index(CONTRACT_STOP)
    return text[start:stop].strip()


def build_messages(contract: str, prompt: str) -> list[dict[str, str]]:
    system = (
        "你是 pax-family 的统一编排入口 pax-orchestrate。严格遵守下面给你的工作流契约，"
        "不要引入契约之外的规则，也不要替用户补充他没有说明的信息。\n"
        "如果输入缺少契约所需的上下文，就按契约本身的判定规则做出最合理的判断，"
        "并在 reasoning 里说明你依赖了哪些信号。\n\n"
        "只返回 JSON，不要 markdown 包裹：\n"
        '{"primary_intent": "<diagnose_fix|feature_dev|refactor|data_ops|doc_consult|tool_build>",\n'
        ' "secondary_intent": ["<performance|security|data_integrity|ux_error|integration|deployment>", ...],\n'
        ' "irreversibility": 1|2|3, "impact_scope": 1|2|3,\n'
        ' "uncertainty": 1|2|3, "coordination_cost": 1|2|3,\n'
        ' "risk_score": <总分整数>, "risk_level": "<low|medium|high>",\n'
        ' "diagnose_required": true|false,\n'
        ' "route": ["pax-clarify", ...],\n'
        ' "storage_backend_required": true|false,\n'
        ' "cross_repo": true|false,\n'
        ' "execution_strategy_required": true|false,\n'
        ' "reasoning": "一句话：依赖了哪些输入信号"}\n\n'
        "--- 工作流契约（原文） ---\n" + contract
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "用户目标：\n" + prompt},
    ]


def parse_selection(text: str) -> dict:
    t = text.strip().strip("`")
    if t.lower().startswith("json"):
        t = t[4:]
    lb, rb = t.find("{"), t.rfind("}")
    if lb != -1 and rb != -1:
        t = t[lb : rb + 1]
    data = json.loads(t)
    # bool 在 Python 里是 int 的子类，先把布尔字段拎出来再判 int
    raw = data.get("risk_score")
    data["risk_score"] = int(round(float(raw))) if raw is not None else None
    for key in ("irreversibility", "impact_scope", "uncertainty", "coordination_cost"):
        value = data.get(key)
        data[key] = int(round(float(value))) if value is not None else None
    data["diagnose_required"] = bool(data.get("diagnose_required", False))
    data["storage_backend_required"] = bool(data.get("storage_backend_required", False))
    data["cross_repo"] = bool(data.get("cross_repo", False))
    data["execution_strategy_required"] = bool(data.get("execution_strategy_required", False))
    data["secondary_intent"] = list(data.get("secondary_intent") or [])
    data["route"] = list(data.get("route") or [])
    return data


def score_case(case: dict, actual: dict) -> dict:
    """按 case 的 category 打分。逐字段判定，避免只给一个笼统的 pass。"""
    exp, checks, wrong = case["expected"], [], []

    def add(name: str, got, want, note: str = "", undefined_in_contract: bool = False):
        ok = got == want
        item = {"check": name, "passed": ok, "expected": want, "actual": got}
        if undefined_in_contract:
            item["undefined_in_contract"] = True
        checks.append(item)
        if not ok:
            wrong.append(name + (f" ({note})" if note else ""))

    if case["category"] == "intent_classification":
        add("primary_intent", actual.get("primary_intent"), exp["primary_intent"])
        add("secondary_intent", sorted(actual.get("secondary_intent", [])),
            sorted(exp["secondary_intent"]))
        # 契约缺口：gold 要求 confidence，但 W1–W4 从未定义该字段，模型只能返回 None。
        add("confidence", actual.get("confidence"), exp.get("confidence"),
            "gold 要求 confidence，但 SKILL.md W1–W4 没有定义该字段",
            undefined_in_contract=True)

    elif case["category"] == "risk_scoring":
        for dim in ("irreversibility", "impact_scope", "uncertainty", "coordination_cost"):
            add(dim, actual.get(dim), exp[dim])
        add("risk_score", actual.get("risk_score"), exp["risk_score"])
        add("risk_level", actual.get("risk_level"), exp["risk_level"])

    elif case["category"] == "route_building":
        add("route", actual.get("route"), exp["route"])
        add("diagnose_required", actual.get("diagnose_required"), exp["diagnose_required"])
        add("storage_backend_required", actual.get("storage_backend_required"),
            exp["storage_backend_required"])

    elif case["category"] == "cross_repo_detection":
        add("cross_repo", actual.get("cross_repo"), exp["cross_repo"])
        add("execution_strategy_required", actual.get("execution_strategy_required"),
            exp["execution_strategy_required"])

    else:
        raise ValueError(f"未知 category: {case['category']}")

    return {"passed": not wrong, "failed_checks": wrong, "checks": checks}


# gold 数据集要求、但 SKILL.md W1–W4 契约中不存在这些字段。
# 它们的失败是 gold/契约不一致，不是模型能力问题，必须从模型口径里剔除。
GOLD_CONTRACT_UNDEFINED: tuple[str, ...] = ("confidence",)

# gold 与契约本身冲突、或契约无法从 prompt 支撑 gold 的条目。
# 这些 FAIL 不能计入模型能力，修订数据集时应逐条核对。
GOLD_CONTRACT_ISSUES: list[dict] = [
    {
        "scope": "intent_classification 全部 7 条",
        "field": "confidence",
        "issue": "gold 每条都要求 confidence（high/medium/low），但 SKILL.md W1–W4 从未定义该字段，"
                 "模型只能返回 None，21 次判定全灭。属数据集字段超前于契约，不是分类能力问题。",
        "model_actual": "primary_intent 21/21 全对；secondary_intent 19/21",
        "fix": "二选一：在 W1 增加 confidence 定义与判定规则，或从数据集与评测里删掉该字段。",
    },
    {
        "case_id": "pax-risk-high-01",
        "field": "irreversibility / impact_scope / risk_score / risk_level",
        "issue": "gold 内部自洽（3+3+2+2=10 → high，且命中 W2「不可逆性 3 且影响范围 3 → 强制 high」），"
                 "但四维取值无法从 prompt 推导：契约对 impact_scope=3 的标准是“系统级、跨团队、跨系统、全用户”，"
                 "prompt 仅说“把旧表的数据迁移到新表”，无系统级信号。模型三次一致返回 2/2/2/2=8 (medium)。",
        "model_actual": "2/2/2/2 → risk_score 8, risk_level medium",
        "fix": "契约需要给出数据迁移类任务的 impact_scope 判定基准（例如“影响行数/表数量/是否含主链路”），"
               "否则 gold 只能靠出题人直觉，不同执行者会得到不同答案。",
    },
    {
        "case_id": "pax-route-df-01",
        "field": "storage_backend_required",
        "issue": "gold 给 secondary_intent=[] 但要求 storage_backend_required=true。而契约 W4 的条件是"
                 "`if intent.primary == 「data_ops」 or 「data_integrity」 in intent.secondary`——本案例 primary=diagnose_fix、"
                 "secondary=[]，两个条件都不满足，契约强制为 false。gold 按契约自身的逻辑就是错的。",
        "model_actual": "三次一致返回 false（严格按契约）",
        "fix": "若要覆盖“任何涉及存储后端问题的诊断都要确认存储后端”这个直觉，需改契约 W4 的条件；"
               "否则应把 gold 改为 false，或把 secondary_intent 补上 data_integrity。",
    },
    {
        "case_id": "pax-intent-df-01",
        "field": "secondary_intent",
        "issue": "gold 给 secondary_intent=[]，但契约对 ux_error 的触发条件写的是“前端报错、交互异常、UI 缺陷”。"
                 "本案例是表单字段校验报错——算不算“交互异常”契约没有给出样例，模型三次运行在 1/3 概率下标为 ux_error。",
        "model_actual": "secondary_intent 在 [] 与 ['ux_error'] 之间摆动（3 次中 1 次为 ux_error）",
        "fix": "在 W1 的 ux_error 行补一个正例/反例（表单字段校验类算不算），否则这是不可解的歧义。",
    },
]


def call_model(messages: list[dict]) -> tuple[dict | None, dict, str | None]:
    import openai
    client = openai.OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=API_BASE)
    resp = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0,
        response_format={"type": "json_object"}, timeout=120,
    )
    text = resp.choices[0].message.content or ""
    usage = {"input_tokens": resp.usage.prompt_tokens,
             "output_tokens": resp.usage.completion_tokens}
    try:
        return parse_selection(text), usage, None
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return None, usage, f"模型输出无法解析为路由 JSON：{e!r}"


def summarize(rows: list[dict]) -> dict:
    """从逐行结果重算汇总。--rescore 和主流程共用，保证口径一致。"""
    total = len(rows)
    adjusted_ok = [r for r in rows
                   if all(c["passed"] for c in r["checks"] if c["check"] not in GOLD_CONTRACT_UNDEFINED)]
    raw_passed = sum(r["passed"] for r in rows)
    categories = sorted({r["category"] for r in rows})
    by_cat = {}
    for cat in categories:
        cr = [r for r in rows if r["category"] == cat]
        adj = [r for r in cr
               if all(c["passed"] for c in r["checks"] if c["check"] not in GOLD_CONTRACT_UNDEFINED)]
        by_cat[cat] = {
            "total": len(cr), "passed_raw": sum(r["passed"] for r in cr),
            "passed_adjusted": len(adj),
            "accuracy_raw": round(100 * sum(r["passed"] for r in cr) / len(cr), 1),
            "accuracy_adjusted": round(100 * len(adj) / len(cr), 1),
        }
    check_hits: dict[str, list[bool]] = {}
    for r in rows:
        for c in r["checks"]:
            check_hits.setdefault(c["check"], []).append(c["passed"])
    by_check = {k: {"passed": sum(v), "total": len(v)} for k, v in sorted(check_hits.items())}
    flaky = []
    for case_id in sorted({r["case_id"] for r in rows}):
        per = [r["passed"] for r in rows if r["case_id"] == case_id]
        if 0 < per.count(True) < len(per):
            flaky.append({"case_id": case_id, "per_repeat": per})
    return {
        "summary": {"total": total, "passed": raw_passed, "failed": total - raw_passed,
                    "accuracy": round(100 * raw_passed / total, 1) if total else 0.0,
                    "note": "原始口径，包含 gold 要求但契约未定义的字段，不可单独引用"},
        "summary_adjusted": {
            "total": total, "passed": len(adjusted_ok),
            "failed": total - len(adjusted_ok),
            "accuracy": round(100 * len(adjusted_ok) / total, 1) if total else 0.0,
            "excluded_checks": list(GOLD_CONTRACT_UNDEFINED),
            "note": "剔除 gold/契约不一致字段后的模型真实表现",
        },
        "by_category": by_cat,
        "by_check": by_check,
        "stability": {
            "repeats": len({r["repeat"] for r in rows}) or None,
            "flaky_cases": flaky,
            "flaky_count": len(flaky),
            "total_cases": len({r["case_id"] for r in rows}),
        },
        "gold_contract_issues": GOLD_CONTRACT_ISSUES,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="只打印将发送的提示，不调 API")
    ap.add_argument("--repeats", type=int, default=1, help="每个案例重复几次")
    ap.add_argument("--dataset", default=str(DATASET))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--rescore", action="store_true",
                    help="不重新调用模型，用已有结果重算汇总")
    args = ap.parse_args()

    contract = extract_contract()
    cases = json.loads(Path(args.dataset).read_text(encoding="utf-8"))["cases"]
    messages = build_messages(contract, cases[0]["prompt"])
    print(f"数据集：{len(cases)} 案例 | 模型：{MODEL} @ {API_BASE}")
    print(f"契约：W1–W4，{len(contract)} 字符 | 系统提示 {len(messages[0]['content'])} 字符")

    if args.dry_run:
        print(f"\n{'=' * 72}\n系统提示（完整内容，将发给模型）\n{'=' * 72}")
        print(messages[0]["content"])
        print(f"\n{'=' * 72}\n用户消息（示例：{cases[0]['id']}）\n{'=' * 72}")
        print(messages[1]["content"])
        print(f"\n将发起 {len(cases)} × {args.repeats} = {len(cases) * args.repeats} 次请求")
        return 0

    if args.rescore:
        # 只重算汇总，不重新调用模型
        out = Path(args.out)
        if not out.exists():
            print(f"错误：找不到已有结果 {out}", file=sys.stderr)
            return 1
        saved = json.loads(out.read_text(encoding="utf-8"))
        result = {**summarize(saved["results"]),
                  "usage": saved.get("usage", {}), "meta": saved.get("meta", {}),
                  "results": saved["results"]}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print_summary(result)
        return 0 if result["summary_adjusted"]["accuracy"] >= 80 else 1

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("错误：DEEPSEEK_API_KEY 未设置", file=sys.stderr)
        return 1

    rows, usage_total = [], {"input_tokens": 0, "output_tokens": 0}
    for case in cases:
        for rep in range(args.repeats):
            messages = build_messages(contract, case["prompt"])
            actual, usage, err = call_model(messages)
            for k in usage_total:
                usage_total[k] += usage.get(k, 0)
            verdict = score_case(case, actual or {}) if actual else None
            row = {
                "case_id": case["id"], "category": case["category"], "repeat": rep,
                "prompt": case["prompt"], "expected": case["expected"],
                "actual": actual, "error": err,
                "passed": bool(verdict and verdict["passed"]),
                "failed_checks": verdict["failed_checks"] if verdict else [],
                "checks": verdict["checks"] if verdict else [],
                "reasoning": (actual or {}).get("reasoning"),
                "input_tokens": usage.get("input_tokens"),
            }
            rows.append(row)
            mark = "PASS" if row["passed"] else ("ERR" if err else "FAIL")
            print(f"  [{mark}] {case['id']} r{rep}"
                  + (f"  ← {'; '.join(row['failed_checks'])}" if not row["passed"] else ""))

    summary = summarize(rows)
    result = {
        **summary,
        "usage": {**usage_total, "model": MODEL, "api_base": API_BASE,
                  "contract_source": "skills/pax-orchestrate/SKILL.md#W1-W4",
                  "contract_chars": len(contract)},
        "meta": {
            "version": "2.0", "repeats": args.repeats,
            "run_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
            "note": "系统提示 = SKILL.md W1–W4 原文，未注入契约外澄清；gold 与契约冲突的判为 FAIL",
        },
        "results": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print_summary(result)
    print(f"\n结果已保存至：{out}")
    return 0 if result["summary_adjusted"]["accuracy"] >= 80 else 1


def print_summary(result: dict) -> None:
    """打印双口径汇总。"""
    adj, raw = result["summary_adjusted"], result["summary"]
    print(f"\n总计（原始口径，含 gold/契约不一致字段）：{raw['passed']}/{raw['total']} ({raw['accuracy']}%)")
    print(f"总计（剔除契约未定义字段，模型真实表现）：{adj['passed']}/{adj['total']} ({adj['accuracy']}%)")
    print(f"      剔除的检查项：{', '.join(adj['excluded_checks'])}")
    print("\n按类别：")
    for cat, s in result["by_category"].items():
        print(f"  {cat:24} {s['passed_adjusted']:2}/{s['total']:<2} ({s['accuracy_adjusted']:5}%)"
              f"   ← 原始 {s['passed_raw']}/{s['total']} ({s['accuracy_raw']}%)")
    st = result.get("stability", {})
    if st:
        names = ", ".join(f["case_id"] for f in st["flaky_cases"]) if st["flaky_cases"] else ""
        print(f"\n稳定性：{st['flaky_count']}/{st['total_cases']} 个案例跨 {st['repeats']} 次不一致{names and '：' + names or ''}")
    issues = result.get("gold_contract_issues", [])
    if issues:
        print(f"\ngold/契约问题 {len(issues)} 项（不计入模型能力）：")
        for it in issues:
            print(f"  - [{it.get('scope') or it.get('case_id')}] {it.get('field')}")


if __name__ == "__main__":
    sys.exit(main())
