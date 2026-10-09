#!/usr/bin/env python3
"""指令遵守评估 runner：量化 AGENTS.md 强规则被注入后，模型面对任务是否先把
pax-orchestrate 作为第一步。

复用 internal routing eval 的模型调用链（openai + DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL）。
对比强弱两种 AGENTS.md 措辞在同一批任务上的遵守率（first_action_is_orchestrate）。

用法：
    python evals/run_ic_eval.py                    # 真实运行（weak+strong × N cases）
    python evals/run_ic_eval.py --dry-run          # 只打印将发送的提示，不调 API
    python evals/run_ic_eval.py --tpl weak         # 只跑某一种措辞
    python evals/run_ic_eval.py --repeats 3        # 稳定性（视 API 预算而定）

密钥与端点从环境变量取（DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL），本文件不存值。
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
DATASET = ROOT / "evals" / "datasets" / "instruction-compliance" / "ic_v1.0.json"
OUT = ROOT / "evals" / "results" / "instruction_compliance_results.json"
MODEL = os.environ.get("INTERNAL_EVAL_MODEL", "deepseek-flash")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def load_dataset() -> dict:
    with open(DATASET, encoding="utf-8") as f:
        return json.load(f)


def build_messages(instructions: str, task: str) -> list[dict[str, str]]:
    system = (
        "你是运行在某个已接入 pax-family 项目中的 AI 开发助手。\n"
        "下面先给出你所在项目的指令约定（project_instructions），请严格遵守。\n"
        "你收到一个任务时，必须用一句话告诉用户你的第一步会做什么；不要真的执行文件操作。\n"
        "如果按照约定你应该先走 pax-family 编排入口，请在你的第一步说明中明确写出"
        "『先调用 pax-orchestrate 编排入口』，否则说明你会直接动手。\n\n"
        "只输出你的第一步动作说明（一句话即可），不要写代码。\n\n"
        f"【项目指令】\n{instructions}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"任务：{task}\n\n请告诉我你处理这个任务的第一步会做什么。"},
    ]


def call_model(messages: list[dict]) -> tuple[str | None, bool]:
    """返回 (content, api_error)。api_error=True 表示调用失败。"""
    import openai
    client = openai.OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=API_BASE)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip(), False
    except Exception as exc:  # noqa: BLE001 — 如实记录每一类失败
        return f"[API错误] {exc}", True


def judge(content: str | None) -> tuple[bool, str]:
    """判断第一步是否为 orchestrate。"""
    if not content:
        return False, "empty"
    s = content.lower()
    hit = ("pax-orchestrate" in s) or ("编排入口" in s) or ("先走编排" in s)
    # 反向排除：明确说"直接动手/直接修改/先看代码"却没提编排
    direct = any(k in s for k in ("直接修改", "先看看代码", "直接动手", "先定位", "直接改"))
    if hit:
        return True, "orchestrate-first"
    if direct:
        return False, "direct-first"
    return False, "ambiguous"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tpl", choices=["weak", "strong", "both"], default="both")
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    ds = load_dataset()
    templates = ds["templates"]
    templates_to_run: list[tuple[str, str]] = []
    tpl_keys = [k for k in templates if k.startswith("weak_")] + [k for k in templates if k.startswith("strong_")]
    for key in tpl_keys:
        tpl_short = "weak" if key.startswith("weak_") else "strong"
        if args.tpl in ("both", tpl_short):
            templates_to_run.append((tpl_short, templates[key]))

    if not args.dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        print("错误：DEEPSEEK_API_KEY 未设置（可用 --dry-run 查看提示）", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for tpl_key, tpl_text in templates_to_run:
        for case in ds["cases"]:
            for r in range(args.repeats):
                messages = build_messages(tpl_text, case["task"])
                row = {
                    "id": case["id"],
                    "category": case["category"],
                    "tpl": tpl_key,
                    "repeat": r + 1,
                    "expected": case["expected_first_action"],
                    "task": case["task"],
                }
                if args.dry_run:
                    row["prompt_preview"] = messages[0]["content"][:200]
                    rows.append(row)
                    continue
                content, api_error = call_model(messages)
                passed, verdict = judge(content)
                if api_error:
                    passed, verdict = False, "api_error"
                row.update({"response": content, "passed": passed, "verdict": verdict})
                rows.append(row)

    # 汇总
    summary = {"version": ds["version"], "templates_run": [t for t, _ in templates_to_run],
               "dry_run": args.dry_run, "rows": rows}
    if not args.dry_run:
        per_tpl: dict[str, dict] = {}
        for tpl_key, _ in templates_to_run:
            subset = [r for r in rows if r["tpl"] == tpl_key and r.get("verdict") not in ("api_error",)]
            total = len(subset)
            passed = sum(1 for r in subset if r["passed"])
            per_tpl[tpl_key] = {"total": total, "passed": passed,
                                "compliance": (passed / total) if total else None}
        summary["per_template"] = per_tpl
        if "both" in [t for t, _ in templates_to_run] and len(per_tpl) == 2:
            w = per_tpl["weak"]["compliance"]
            s = per_tpl["strong"]["compliance"]
            delta = (s - w) if (w is not None and s is not None) else None
            summary["delta_strong_minus_weak"] = delta
    else:
        summary["note"] = "dry-run：未调用 API，只在 rows 里放了 prompt 预览，供检查措辞。"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
