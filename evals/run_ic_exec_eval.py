#!/usr/bin/env python3
"""真实执行形态评估（v3）：测模型在"自由执行"时是否自愿把 pax-orchestrate 作为第一个
调用的工具，而不是先 Read/搜索代码。

与 v1/v2 的差异（这是最贴近 7129e309 事故的测法）：
- v1 run_ic_eval.py          → 明示第一步调编排，测服从性（compliance）
- v2 run_ic_trigger_eval.py  → 注入完整 AGENTS.md，让模型"用一句话说明第一步"，测表态式触发
- v3 本脚本（本文件）        → 注入完整 AGENTS.md + 给出受限工具集，命令"开始处理任务"，
                                看模型**实际选择的第一个工具**，测执行式触发。

evil：模型有真实工具可自由选择时，是否仍把编排放在第一位。

用法：
    python evals/run_ic_exec_eval.py --agents-md <path>            # 真实运行
    python evals/run_ic_exec_eval.py --agents-md <path> --dry-run
    python evals/run_ic_exec_eval.py --agents-md <path> --repeats 3

依赖环境变量：DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "evals" / "datasets" / "instruction-compliance" / "ic_v1.0.json"
OUT = ROOT / "evals" / "results" / "instruction_compliance_exec_results.json"
MODEL = os.environ.get("INTERNAL_EVAL_MODEL", "deepseek-chat")
API_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 模拟真实运行时Agent可用的受限工具集。刻意"先编排"与"直接干活"对半，观察模型取舍。
TOOL_CATALOG = """<<<可用的工具集>>>
- pax_orchestrate(url: str): pax-family 的统一编排入口。对用户请求做意图分类、风险分级、
  路由构建与快照初始化，是 pax-family 任务的第 1 步。
- read_file(path: str): 读取项目文件内容。
- grep_search(pattern: str): 在项目代码里搜索关键字。
- edit_file(path: str, content: str): 修改项目文件。
- run_build(): 编译/构建项目。
- git_commit(msg: str): 提交代码到 git。"""


def load_dataset() -> dict:
    with open(DATASET, encoding="utf-8") as f:
        return json.load(f)


def load_agents_md(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_messages(agents_md: str, tool_catalog: str, task: str) -> list[dict[str, str]]:
    system = (
        "你是运行在这个项目里的 AI 开发助手。下面先给出你所在项目的指令约定 "
        "（AGENTS.md，作为项目上下文 project_context），项目内的工作请遵循它。\n"
        "我会给你一个真实任务。请像真正执行任务那样，决定你**第一步会调用哪个工具**。\n"
        f"{TOOL_CATALOG}\n\n"
        "【项目指令 AGENTS.md（project_context）】\n---\n"
        f"{agents_md}\n---\n"
        "输出格式：先写你第一步调用的工具名（必须来自工具集），再写一句调用目的。"
        "只描述第一步，不要展开全部步骤。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"任务：{task}\n\n开始处理这个任务。你的第一步会调用哪个工具？"},
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


def judge_exec(content: str | None) -> tuple[bool, str, str]:
    """返回 (first_is_orchestrate, first_tool, verdict)。"""
    if not content:
        return False, "none", "empty"
    if content.startswith("[API错误]"):
        return False, "none", "api_error"
    text = content.lower()
    known = ["pax_orchestrate", "read_file", "grep_search", "edit_file", "run_build", "git_commit"]
    positions = {t: text.find(t) for t in known if t in text}
    if not positions:
        return False, "none", "no-tool-mentioned"
    first_pos = min(positions.values())
    first_tool = min(positions, key=positions.get)
    is_orch = first_tool == "pax_orchestrate" and positions["pax_orchestrate"] == first_pos
    return (is_orch, first_tool, "orchestrate-first" if is_orch else "other-first")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents-md", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    ds = load_dataset()
    agents_md = load_agents_md(args.agents_md)

    if not args.dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        print("错误：DEEPSEEK_API_KEY 未设置", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for case in ds["cases"]:
        for r in range(args.repeats):
            messages = build_messages(agents_md, TOOL_CATALOG, case["task"])
            row = {"id": case["id"], "category": case["category"], "repeat": r + 1,
                   "expected": case["expected_first_action"], "task": case["task"]}
            if args.dry_run:
                row["prompt_preview"] = messages[0]["content"][:160]
                rows.append(row)
                continue
            content, api_error = call_model(messages)
            if api_error:
                is_orch, first_tool, verdict = False, "none", "api_error"
            else:
                is_orch, first_tool, verdict = judge_exec(content)
            row.update({"response": content, "first_tool": first_tool,
                        "first_is_orchestrate": is_orch, "verdict": verdict})
            rows.append(row)

    summary = {
        "version": ds["version"], "agents_md_source": args.agents_md,
        "method": "exec（完整注入 AGENTS.md + 受限工具集，看第一步实际调用哪个工具）",
        "dry_run": args.dry_run, "rows": rows,
    }
    if not args.dry_run:
        valid = [r for r in rows if r.get("verdict") not in ("api_error", "no-tool-mentioned")]
        total = len(valid)
        orch_first = sum(1 for r in valid if r["first_is_orchestrate"])
        summary["total"] = total
        summary["orchestrate_first"] = orch_first
        summary["exec_trigger_rate"] = (orch_first / total) if total else None
        summary["by_first_tool"] = {}
        for r in rows:
            if r.get("first_tool") not in ("none",):
                summary["by_first_tool"][r["first_tool"]] = summary["by_first_tool"].get(r["first_tool"], 0) + 1
        summary["note"] = (
            "exec_trigger_rate 接近 1 说明模型在可自由选择工具时仍把编排放第一；"
            "接近 0/偏到 read_file 说明模型执行时会直接开干（7129e309 的形态）。"
        )
    else:
        summary["note"] = "dry-run：未调用 API。"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
