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


def validate_response(case: dict, actual: dict) -> list[str]:
    """返回该行违反契约的列表（空 = 自洽）。

    JSON 能解析不等于输出可用。模型可以吐出一份语法合法但自相矛盾的 JSON——
    比如四个维度都是 1 却报 risk_score=0（四维最小和是 4），或 route 为空却声明
    diagnose_required。这类输出不能算「判断错」，它根本没做出判断；
    混进能力分会把能力分和输出健壮性混成一团，问题也就定位不到。
    """
    bad: list[str] = []
    dims = ("irreversibility", "impact_scope", "uncertainty", "coordination_cost")
    vals = [actual.get(k) for k in dims]
    if all(isinstance(v, int) for v in vals) and isinstance(actual.get("risk_score"), int):
        if sum(vals) != actual["risk_score"]:
            bad.append(f"risk_score={actual['risk_score']} ≠ 四维之和 {sum(vals)}")
    if actual.get("diagnose_required") and not actual.get("route"):
        bad.append("diagnose_required=true 但 route 为空")
    if case.get("category") == "route_building" and not actual.get("route"):
        bad.append("route_building 题返回空 route")
    return bad


def _norm_skill(x) -> str:
    """路由步骤名归一化：去 pax- 前缀、小写、去首尾空格。

    契约 W4 写的是短名（clarify），早期 gold 写成全名（pax-clarify）。
    两者是同一份路由的两种记法，记法差异不应被算成路由错误。
    """
    s = str(x).strip().lower()
    return s[4:] if s.startswith("pax-") else s


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

    elif case["category"] == "risk_scoring":
        for dim in ("irreversibility", "impact_scope", "uncertainty", "coordination_cost"):
            add(dim, actual.get(dim), exp[dim])
        add("risk_score", actual.get("risk_score"), exp["risk_score"])
        add("risk_level", actual.get("risk_level"), exp["risk_level"])

    elif case["category"] == "route_building":
        got_route, want_route = list(actual.get("route") or []), list(exp["route"] or [])
        norm_got, norm_want = [_norm_skill(x) for x in got_route], [_norm_skill(x) for x in want_route]
        variant = (got_route != want_route and norm_got == norm_want)
        add("route", norm_got, norm_want,
            note="命名格式变体（pax- 前缀差异，步骤与顺序一致）" if variant else "")
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


# v1.0 的 gold 与契约冲突项已在数据集 v1.1 中解决（见 fix_internal_dataset.py）。
# 保留完整记录是为了让 results/ 里的历史数字可追溯、可复核。
GOLD_CONTRACT_RESOLUTIONS: list[dict] = [
    {
        "case_id": "intent_classification 全部 7 条",
        "field": "confidence",
        "v1_0_problem": "gold 要求 confidence（high/medium/low），但 W1–W4 从未定义该字段，"
                        "21 次判定全灭。数据集字段超前于契约。",
        "resolution": "已解决（改 gold）：从数据集删除该字段。",
        "why_not_contract": "W2–W4 没有任何逻辑读取 confidence，是个装饰字段。"
                            "为了让测试通过而给契约补一个下游无人使用的字段，等于反向从测试推导契约。",
    },
    {
        "case_id": "pax-risk-high-01",
        "field": "irreversibility / impact_scope",
        "v1_0_problem": "gold 3/3/2/2=10 自洽，但原 prompt「把旧表的数据迁移到新表」"
                        "无系统级信号，impact_scope=3 无法从 prompt 推导。模型三次一致给 2/2/2/2。",
        "resolution": "已解决（改 prompt）：补为「生产环境账务模块、30 张表、约 800 万行、"
                      "无法回滚重跑」，命中 impact_scope=3 的三条基准。gold 与契约未动。",
        "why_not_gold": "gold 编码的其实是正确的工程判断（生产账务数据迁移就是高风险），"
                        "问题在于题面没给信号，属不可解题而非模型能力问题。",
    },
    {
        "case_id": "pax-route-df-01",
        "field": "storage_backend_required",
        "v1_0_problem": "gold 隐含 secondary=[] 却要求 storage_backend_required=true，"
                        "而 W4 的条件（primary==data_ops 或 'data_integrity' in secondary）"
                        "两个都不满足，契约强制 false。gold 按契约自身逻辑就是错的。",
        "resolution": "已解决（改 gold）：与 pax-intent-df-01 一起把 secondary 改为 ['data_integrity']，"
                      "W4 条件成立，storage_backend_required=true 与契约一致。契约未动。",
        "why_not_contract": "契约 W4 的布尔条件清晰可判定；改契约去迎合一个错误的 gold 是方向反了。",
    },
    {
        "case_id": "pax-intent-df-01",
        "field": "secondary_intent",
        "v1_0_problem": "gold 给 []，模型在 [] 与 ['ux_error'] 之间摆动（3 次中 1 次）。"
                        "模型标的是 ux_error，而 prompt 是字段值校验失败。",
        "resolution": "双管齐下：(1) 改 gold 为 ['data_integrity']——契约对 data_integrity 的定义"
                      "含「字段错误」，是更贴切的标签，gold 原本漏标；"
                      "(2) 契约 W1 补易混淆边界（校验报错归 data_integrity，不归 ux_error），"
                      "防止未来题目继续在这里摆动。",
    },
]

# ---------------------------------------------------------------------------
# 发布门槛（2026-10-02 定义）
#
# 门槛按契约的确定性分档，**不是**从单次测量反推的——那样等于把门槛设成
# 「刚好低于本次成绩」，保证通过且毫无信号。样本量也太小（n=9 或 n=3），
# 一次判定偏差就能移动 11–33pp，所以这些门槛是**回归警报**，不是质量证明：
# 跌破才需要调查，达标不等于契约实现得完美。
# ---------------------------------------------------------------------------
GATE_CHECKS: dict[str, float] = {
    # 契约写成查表 / MECE 分类 / 显式布尔条件：一个正确实现应当几乎永远对。
    "primary_intent": 0.95,
    "diagnose_required": 0.95,
    "cross_repo": 0.95,
    "execution_strategy_required": 0.95,
    # 查表结果的链式拼接，误差会随链条放大，留一档余量。
    "route": 0.90,
    "storage_backend_required": 0.90,
    # 可叠加标签 + 语义边界判定（ux_error / data_integrity）。
    "secondary_intent": 0.85,
    # 聚合值：单维误差可能被其他维抵消，但强制升级规则需要稳定。
    "risk_score": 0.85,
    "risk_level": 0.85,
    # 1–3 主观量纲，契约只给示例不给阈值，最难收敛。
    "irreversibility": 0.80,
    "impact_scope": 0.80,
    "uncertainty": 0.80,
    "coordination_cost": 0.80,
}

GATE_CATEGORY: dict[str, float] = {
    "intent_classification": 0.95,
    "risk_scoring": 0.85,
    "route_building": 0.90,
    "cross_repo_detection": 0.90,
}

# 总门槛：剔除 gold/契约冲突字段后的整体准确率。v1.0 用的 0.80 是随手写的声明值。
GATE_OVERALL = 0.90

# 输出健壮性：模型必须按契约吐合法且自洽的 JSON。低于此值说明路由输出本身不可靠，
# 能力分再高也没用。n=42 时允许至多 2 次失败（97.6%）。
GATE_VALID_RATE = 0.95


# v1.0 遗留：gold 要求、契约从未定义的字段。v1.1 已删，保留空集仅为兼容性。
GOLD_CONTRACT_UNDEFINED: tuple[str, ...] = ()


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
    """从逐行结果重算汇总。--rescore 和主流程共用，保证口径一致。

    三个口径：
      原始     包含 gold 要求但契约未定义的字段（v1.1 后已无）
      调整     剔除 gold/契约不一致字段
      可解析   再剔除「模型没返回合法 JSON」的行。那类失败是输出健壮性问题，
               不是路由判断能力；混在一起会把能力分污染，门槛也失去意义。
    """
    parsable = [r for r in rows if r.get("actual")]
    parse_fails = [r for r in rows if not r.get("actual")]
    struct_bad = [r for r in parsable if validate_response(
        {"category": r.get("category")}, r["actual"])]
    struct_ids = {(r["case_id"], r["repeat"]) for r in struct_bad}
    # 能力口径的分母：既成功解析、又不违反契约自洽的行
    valid = [r for r in parsable if (r["case_id"], r["repeat"]) not in struct_ids]
    fails = parse_fails + struct_bad

    def adj_ok(rs: list[dict]) -> list[dict]:
        return [r for r in rs
                if all(c["passed"] for c in r["checks"]
                       if c["check"] not in GOLD_CONTRACT_UNDEFINED)]

    def pct(n: int, d: int) -> float:
        return round(100 * n / d, 1) if d else 0.0

    total = len(rows)
    adjusted_ok = adj_ok(rows)
    raw_passed = sum(r["passed"] for r in rows)
    categories = sorted({r["category"] for r in rows})
    by_cat = {}
    for cat in categories:
        cr = [r for r in rows if r["category"] == cat]
        cp_valid = [r for r in cr
                    if r.get("actual") and (r["case_id"], r["repeat"]) not in struct_ids]
        adj = adj_ok(cr)
        by_cat[cat] = {
            "total": len(cr), "passed_raw": sum(r["passed"] for r in cr),
            "passed_adjusted": len(adj),
            "accuracy_raw": pct(sum(r["passed"] for r in cr), len(cr)),
            "accuracy_adjusted": pct(len(adj), len(cr)),
            # 能力分：分母只算自洽且解析成功的行
            "parsable": len(cp_valid),
            "passed_parsable": len(adj_ok(cp_valid)),
            "accuracy_parsable": pct(len(adj_ok(cp_valid)), len(cp_valid)),
        }
    check_hits: dict[str, list[bool]] = {}
    for r in valid:                        # 只看自洽且解析成功的行
        for c in r["checks"]:
            check_hits.setdefault(c["check"], []).append(c["passed"])
    by_check = {k: {"passed": sum(v), "total": len(v)} for k, v in sorted(check_hits.items())}

    # holdout 分组：从未被修订过的题 vs 经过 v1.1–v1.4 修订过的题。
    # 这是回答「内部 100% 是不是反拟合出来的」唯一可反复测量的口径。
    # gate 仍按全量口径判定；holdout 只是单独报告项，不参与门槛计算。
    by_holdout = {}
    for flag in (False, True):
        rs = [r for r in rows if bool(r.get("holdout")) == flag]
        vs = [r for r in rs if r.get("actual")
              and (r["case_id"], r["repeat"]) not in struct_ids]
        by_holdout["holdout" if flag else "revised"] = {
            "total": len(rs),
            "cases": len({r["case_id"] for r in rs}),
            "parsable": len(vs),
            "passed_parsable": len(adj_ok(vs)),
            "accuracy_parsable": pct(len(adj_ok(vs)), len(vs)),
            "valid_rate": round(len(vs) / len(rs), 4) if rs else None,
        }

    flaky = []
    for case_id in sorted({r["case_id"] for r in rows}):
        per = [r["passed"] for r in rows if r["case_id"] == case_id]
        if 0 < per.count(True) < len(per):
            flaky.append({"case_id": case_id, "per_repeat": per})
    return {
        "summary": {"total": total, "passed": raw_passed, "failed": total - raw_passed,
                    "accuracy": pct(raw_passed, total),
                    "note": "原始口径，不可单独引用"},
        "summary_adjusted": {
            "total": total, "passed": len(adjusted_ok),
            "failed": total - len(adjusted_ok),
            "accuracy": pct(len(adjusted_ok), total),
            "excluded_checks": list(GOLD_CONTRACT_UNDEFINED),
            "note": "剔除 gold/契约不一致字段；仍包含输出无法解析的行",
        },
        "summary_parsable": {
            "total": len(valid), "passed": len(adj_ok(valid)),
            "failed": len(valid) - len(adj_ok(valid)),
            "accuracy": pct(len(adj_ok(valid)), len(valid)),
            "note": "能力口径：剔除 gold/契约冲突字段，也剔除输出无法解析或自相矛盾的行。gate 以此为准。",
        },
        "robustness": {
            "total": total, "valid": len(valid), "failures": len(fails),
            "parse_rate": round(len(parsable) / total, 4) if total else None,
            "valid_rate": round(len(valid) / total, 4) if total else None,
            "parse_failures": [{"case_id": r["case_id"], "repeat": r["repeat"],
                                "error": r.get("error")} for r in parse_fails],
            "structure_failures": [{"case_id": r["case_id"], "repeat": r["repeat"],
                                    "violations": validate_response(
                                        {"category": r.get("category")}, r["actual"])}
                                   for r in struct_bad],
            "note": "parse_rate 查 JSON 语法；structure_failures 查输出是否自相矛盾"
                    "（如四维都是 1 却报 risk_score=0）。两者都属输出健壮性，不算路由判断能力。",
        },
        "by_category": by_cat,
        "by_check": by_check,
        "by_holdout": by_holdout,
        "stability": {
            "repeats": len({r["repeat"] for r in rows}) or None,
            "flaky_cases": flaky,
            "flaky_count": len(flaky),
            "total_cases": len({r["case_id"] for r in rows}),
        },
        "gold_contract_resolutions": GOLD_CONTRACT_RESOLUTIONS,
    }


def dataset_version() -> str:
    """从数据集顶层读版本号；读不到就返回 unknown。"""
    try:
        return json.loads(Path(DATASET).read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, json.JSONDecodeError):
        return "unknown"


def stamp_meta(meta: dict, *, rescoring: bool, repeats: int | None,
               unchanged: bool = False) -> dict:
    """统一写 meta，避免主流程与 --rescore 两条路径写出两套不一致的元信息。

    run_at 只记录**真实调模型**的时刻；--rescore 不动它。
    graded_at 记录最后一次**实际改变了判定结果**的重判时刻：
    如果重判结果与存档一致，沿用旧值。否则每次 --rescore 时间戳就变，
    同样的评分逻辑重跑得不到字节一致的结果文件，--rescore 就失去了意义。
    """
    meta = dict(meta or {})
    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    if not rescoring:
        meta["run_at"] = now
    meta.update({
        "version": "2.1",
        "dataset_version": dataset_version(),
        **({"repeats": repeats} if repeats else {}),
        # unchanged=True 表示这次重判没改变任何判定，沿用旧 graded_at
        **({"graded_at": now} if rescoring and not unchanged else {}),
        "note": "系统提示 = SKILL.md W1–W4 原文，未注入契约外澄清。"
                "能力分用「可解析且自洽」口径；gold/契约冲突项已逐条解决并记录在 "
                "gold_contract_resolutions 与数据集 changelog。"
                "meta 时间戳由 stamp_meta 维护：run_at 只在真实调用模型时写入，"
                "graded_at 只在重判实际改变判定时刷新，保证同样的评分逻辑重跑得到"
                "字节一致的结果文件。",
    })
    return meta


def check_gate(summary: dict) -> dict:
    """按 GATE_CHECKS / GATE_CATEGORY / GATE_OVERALL 逐项判定。

    能力类门槛用「可解析」口径（剔除 gold/契约冲突字段与输出无法解析的行），
    输出健壮性另走 GATE_PARSE_RATE。两件事混在一起就没法定位问题在哪。

    返回 gate 块：每项的实测值、门槛、pass/fail，以及总判定。
    n 很小的项（cross_repo_detection 只有 1 条题）也照常判定，但结果里标出 n，
    免得把 3 次判定当成分布证据。
    """
    pars = summary["summary_parsable"]
    overall = pars["accuracy"] / 100
    checks = []
    for name, thr in GATE_CHECKS.items():
        hit = summary["by_check"].get(name)
        if not hit:
            continue
        rate = hit["passed"] / hit["total"]
        checks.append({"metric": name, "observed": round(rate, 4),
                       "threshold": thr, "n": hit["total"],
                       "pass": rate >= thr})
    cats = []
    for name, thr in GATE_CATEGORY.items():
        blk = summary["by_category"].get(name)
        if not blk or not blk["parsable"]:
            continue
        rate = blk["accuracy_parsable"] / 100
        cats.append({"metric": f"category:{name}", "observed": round(rate, 4),
                     "threshold": thr, "n": blk["parsable"],
                     "pass": rate >= thr})
    rob = summary["robustness"]
    valid_rate = rob["valid_rate"] if rob["valid_rate"] is not None else 1.0
    robustness = {"metric": "valid_rate", "observed": round(valid_rate, 4),
                  "threshold": GATE_VALID_RATE, "n": rob["total"],
                  "failures": rob["failures"],
                  "parse_failures": len(rob.get("parse_failures", [])),
                  "structure_failures": len(rob.get("structure_failures", [])),
                  "pass": valid_rate >= GATE_VALID_RATE}
    all_pass = ((overall >= GATE_OVERALL) and all(x["pass"] for x in checks + cats)
                and robustness["pass"])
    return {
        "pass": bool(all_pass),
        "overall": {"metric": "accuracy_parsable", "observed": round(overall, 4),
                   "threshold": GATE_OVERALL, "n": pars["total"],
                   "pass": overall >= GATE_OVERALL},
        "robustness": robustness,
        "checks": checks, "categories": cats,
        "failed": [x["metric"] for x in checks + cats if not x["pass"]] +
                  ([] if overall >= GATE_OVERALL else ["accuracy_parsable"]) +
                  ([] if robustness["pass"] else ["valid_rate"]),
        "note": "能力门槛按契约确定性分档，非从单次测量反推。n 很小时一次判定偏差就能移动 11–33pp，"
                "这是回归警报而不是质量证明。",
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
        # 只重算汇总，不重新调用模型。
        # 重要：重打分只有在「模型看到的输入没变」时才有意义。
        # 因此必须校验 prompt 与契约都没漂移，否则宁可拒跑，也不能给出误导性数字。
        out = Path(args.out)
        if not out.exists():
            print(f"错误：找不到已有结果 {out}", file=sys.stderr)
            return 1
        saved = json.loads(out.read_text(encoding="utf-8"))
        rows = saved["results"]
        ds = {c["id"]: c for c in cases}

        stale = []
        for r in rows:
            cid = r.get("case_id")
            c = ds.get(cid)
            if not c:
                stale.append(f"{cid}: 已不在当前数据集中")
            elif r.get("prompt") != c["prompt"]:
                stale.append(f"{cid}: prompt 已变更（旧实测基于旧题面）")
        cur_chars = len(contract)
        old_chars = (saved.get("meta") or {}).get("contract_chars")
        if old_chars and old_chars != cur_chars:
            stale.append(f"契约 W1–W4 已从 {old_chars} 字符变为 {cur_chars} 字符")

        if stale:
            print("✗ --rescore 拒绝：已有结果与当前输入不一致，重打分会产生误导性的数字。")
            for s in dict.fromkeys(stale):
                print(f"  - {s}")
            print("  请去掉 --rescore 重新调用模型。", file=sys.stderr)
            return 2

        # 用当前 gold 重新判定（仅校验通过后才走到这）
        # 先快照旧判定，用于判断这次重判是否真的改变了什么——
        # 没改变就不刷新 graded_at，否则结果文件永远不字节稳定。
        old_verdicts = [(r.get("passed"), tuple(r.get("failed_checks") or [])) for r in rows]
        for r in rows:
            c = ds[r["case_id"]]
            # holdout 是数据集属性，旧结果文件可能没有，按当前数据集补齐
            r["holdout"] = bool(c.get("holdout"))
            verdict = score_case(c, r.get("actual") or {})
            r["expected"], r["checks"] = c["expected"], verdict["checks"]
            r["passed"] = verdict["passed"]
            r["failed_checks"] = verdict["failed_checks"]

        changed = [(r.get("passed"), tuple(r.get("failed_checks") or [])) for r in rows] != old_verdicts

        summary = summarize(rows)
        meta = stamp_meta(saved.get("meta", {}), rescoring=True, repeats=None,
                          unchanged=not changed)
        if changed:
            print("→ 重判改变了判定结果，graded_at 已刷新")
        else:
            print("→ 重判结果与存档一致，graded_at 未变（文件字节可复现）")
        result = {**summary, "gate": check_gate(summary),
                  "usage": saved.get("usage", {}),
                  "meta": meta,
                  "results": rows}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print_summary(result)
        print(f"\n结果已保存至：{out}（--rescore：未调用模型，仅按当前 gold 重判）")
        return 0 if result["gate"]["pass"] else 1

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
                "holdout": bool(case.get("holdout")),
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
        "gate": check_gate(summary),
        "usage": {**usage_total, "model": MODEL, "api_base": API_BASE,
                  "contract_source": "skills/pax-orchestrate/SKILL.md#W1-W4",
                  "contract_chars": len(contract)},
        "meta": stamp_meta({}, rescoring=False, repeats=args.repeats),
        "results": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print_summary(result)
    print(f"\n结果已保存至：{out}")
    return 0 if result["gate"]["pass"] else 1


def print_summary(result: dict) -> None:
    """打印三口径汇总 + 健壮性 + gate。"""
    adj, raw = result["summary_adjusted"], result["summary"]
    par = result["summary_parsable"]
    print(f"\n总计（原始口径）：{raw['passed']}/{raw['total']} ({raw['accuracy']}%)")
    print(f"总计（剔除 gold/契约冲突字段）：{adj['passed']}/{adj['total']} ({adj['accuracy']}%)")
    excl = adj.get("excluded_checks") or []
    print(f"      剔除的检查项：{', '.join(excl) if excl else '（无）'}")
    print(f"总计（可解析口径，能力分）：{par['passed']}/{par['total']} ({par['accuracy']}%)  ← gate 以此为准")
    rob = result["robustness"]
    print(f"输出健壮性：valid_rate = {rob['valid_rate']*100:.1f}%  "
          f"(无效输出 {rob['failures']}/{rob['total']}，其中语法不可解析 "
          f"{len(rob.get('parse_failures', []))}、自相矛盾 "
          f"{len(rob.get('structure_failures', []))})")
    for f in rob.get("parse_failures", []):
        print(f"      - {f['case_id']} r{f['repeat']}: {f['error']}")
    for f in rob.get("structure_failures", []):
        print(f"      - {f['case_id']} r{f['repeat']}: {'; '.join(f['violations'])}")
    print("\n按类别（可解析口径）：")
    for cat, s in result["by_category"].items():
        print(f"  {cat:24} {s['accuracy_parsable']:5}%"
              f"   ({s['passed_parsable']}/{s['parsable']})"
              f"   ← 含解析失败时 {s['accuracy_adjusted']:5}%")
    bh = result.get("by_holdout", {})
    if bh:
        ho, rv = bh.get("holdout", {}), bh.get("revised", {})
        print("\n锁定分组（回答「100% 是不是反拟合出来的」，不参与 gate）：")
        print(f"  修订过的题   {rv.get('accuracy_parsable', 0):5}%"
              f"   ({rv.get('passed_parsable', 0)}/{rv.get('parsable', 0)})"
              f"   {rv.get('cases', 0)} 个 case")
        print(f"  锁定题(holdout) {ho.get('accuracy_parsable', 0):5}%"
              f"   ({ho.get('passed_parsable', 0)}/{ho.get('parsable', 0)})"
              f"   {ho.get('cases', 0)} 个 case")
    st = result.get("stability", {})
    if st:
        names = ", ".join(f["case_id"] for f in st["flaky_cases"]) if st["flaky_cases"] else ""
        print(f"\n稳定性：{st['flaky_count']}/{st['total_cases']} 个案例跨 {st['repeats']} 次不一致{names and '：' + names or ''}")
    # 逐检查项
    print("\n逐检查项（可解析口径，通过率 / 门槛）：")
    for c in result["gate"]["checks"]:
        mark = "✓" if c["pass"] else "✗"
        print(f"  {mark} {c['metric']:26} {c['observed']*100:5.1f}% / ≥{c['threshold']*100:5.1f}%"
              f"   (n={c['n']})")

    g = result.get("gate", {})
    ov = g.get("overall", {})
    rb = g.get("robustness", {})
    verdict = "PASS" if g.get("pass") else "FAIL"
    print(f"\nGATE {verdict} —— 能力 {ov.get('observed', 0)*100:.1f}%"
          f" / ≥{ov.get('threshold', 0)*100:.1f}%  (n={ov.get('n')})")
    print(f"     健壮性 valid_rate {rb.get('observed', 0)*100:.1f}%"
          f" / ≥{rb.get('threshold', 0)*100:.1f}%  (n={rb.get('n')})")
    if g.get("failed"):
        print(f"  未达标：{', '.join(g['failed'])}")
    else:
        print("  全部达标。注：门槛按契约确定性分档，不是质量证明；"
              "n 很小时一次判定偏差就能移动 11–33pp。")

    res = result.get("gold_contract_resolutions", [])
    if res:
        print(f"\ngold/契约冲突 {len(res)} 项（v1.1 已全部解决，不计入模型能力）：")
        for it in res:
            print(f"  - [{it.get('case_id')}] {it.get('field')}")
            print(f"      {it.get('resolution', '')}")


if __name__ == "__main__":
    sys.exit(main())
