#!/usr/bin/env python3
"""触发式(trigger)评估：模拟真实事故的注入结构，测模型是否会自发把 pax-orchestrate
作为第一步。

与 run_ic_eval.py（测"明示编排时的服从性 compliance"）相对：本脚本把**完整 AGENTS.md**
原样注入 system（当作项目上下文 project_context），但**不在指令里明确要求第一步调编排**。
模型是否自发触发编排，才能真实量化 7129e309 那类"没想到要先走"的缺口。

关键区分：
- run_ic_eval.py           → 测 compliance（明示后是否服从）
- run_ic_trigger_eval.py   → 测 trigger（未明示时是否自发想起）

用法：
    python evals/run_ic_trigger_eval.py --agents-md <path>            # 注入指定 AGENTS.md
    python evals/run_ic_trigger_eval.py --agents-md <path> --dry-run
    python evals/run_ic_trigger_eval.py --agents-md <path> --repeats 3

依赖环境变量：DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL（interactive 时由脚本注入）。
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
OUT = ROOT / "evals" / "results" / "instruction_compliance_trigger_results.json"
MODEL = os.environ.get("INTERNAL_EVAL_MODEL", "deepseek-chat")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def load_dataset() -> dict:
    with open(DATASET, encoding="utf-8") as f:
        return json.load(f)


def load_agents_md(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_messages(agents_md: str, task: str) -> list[dict[str, str]]:
    system = (
        "你是运行在这个项目里的 AI 开发助手。下面先给出你所在项目的指令约定"
        "（AGENTS.md，作为项目上下文 project_context），项目内的工作请遵循它。\n"
        "你收到一个任务时，请用一两句话告诉我你处理这个任务的第一步会做什么；"
        "不要真的执行文件操作、不要写代码。只描述你的第一步动作。\n\n"
        "【项目指令 AGENTS.md（project_context）】\n"
        "---\n"
        f"{agents_md}\n"
        "---\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"任务：{task}\n\n请告诉我你处理这个任务的第一步会做什么。"},
    ]


def call_model(messages: list[dict]) -> tuple[str | None, bool]:
    import openai
    client = openai.OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=API_BASE)
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0, max_tokens=120,
        )
        return (resp.choices[0].message.content or "").strip(), False
    except Exception as exc:  # noqa: BLE001
        return f"[API错误] {exc}", True


def judge_trigger(content: str | None) -> tuple[bool, str]:
    """判断第一步是否自发触发编排。"""
    if not content:
        return False, "empty"
    s = content.lower()
    triggered = (
        "pax-orchestrate" in s
        or "编排入口" in s
        or "先走编排" in s
        or "先经过 pax" in s
        or "调用编排" in s
        or "生成快照" in s or "snaPshot" in s.lower() and "pax" in s.lower()
    )
    # 明确直接干活、未提编排
    direct = any(k in s for k in ("直接修改", "先看看代码", "直接动手", "先定位", "先读", "直接改", "查看"))
    if triggered:
        return True, "trigger-orchestrate"
    if direct:
        return False, "direct-first"
    return False, "ambiguous"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents-md", required=True, help="要注入的 AGENTS.md 路径")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    ds = load_dataset()
    agents_md = load_agents_md(args.agents_md)

    if not args.dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        print("错误：DEEPSEEK_API_KEY 未设置（可用 --dry-run 查看提示）", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for case in ds["cases"]:
        for r in range(args.repeats):
            messages = build_messages(agents_md, case["task"])
            row = {
                "id": case["id"], "category": case["category"], "repeat": r + 1,
                "expected": case["expected_first_action"], "task": case["task"],
            }
            if args.dry_run:
                row["prompt_preview"] = messages[0]["content"][:200]
                rows.append(row)
                continue
            content, api_error = call_model(messages)
            passed, verdict = judge_trigger(content)
            if api_error:
                passed, verdict = False, "api_error"
            row.update({"response": content, "triggered": passed, "verdict": verdict})
            rows.append(row)

    summary = {
        "version": ds["version"],
        "agents_md_source": args.agents_md,
        "method": "trigger（完整注入 AGENTS.md，未明示第一步调编排）",
        "dry_run": args.dry_run,
        "rows": rows,
    }
    if not args.dry_run:
        valid = [r for r in rows if r.get("verdict") not in ("api_error",)]
        total = len(valid)
        triggered = sum(1 for r in valid if r["triggered"])
        summary["total"] = total
        summary["spontaneously_triggered"] = triggered
        summary["trigger_rate"] = (triggered / total) if total else None
        summary["by_verdict"] = {}
        for r in valid:
            summary["by_verdict"][r["verdict"]] = summary["by_verdict"].get(r["verdict"], 0) + 1
        summary["note"] = (
            "trigger_rate 接近 1 说明模型会自发先走编排；接近 0 说明 AGENTS.md 虽注入但"
            "模型不会自发想起编排（真实事故 7129e309 的形态）。"
        )
    else:
        summary["note"] = "dry-run：未调用 API，rows 里放 prompt 预览。"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
