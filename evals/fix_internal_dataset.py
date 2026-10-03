#!/usr/bin/env python3
"""pax_internal_routing 数据集修订（v1.0 → v1.2）。

一次性脚本，可重复运行（目标态显式声明，天然幂等）。所有改动都可追溯到
results/internal_routing_results.json 的 gold_contract_resolutions 与 gate 结果，
理由写进数据集的 changelog。

判定原则（贯穿所有修订，也是 v1.2 的起因）：
    gold 的取值必须能「仅凭 prompt + 契约文字」推导出来。
    - prompt 缺信号        → 改 prompt（不是放宽门槛，也不是改契约）
    - 契约标准含糊         → 改契约
    - gold 本身与契约矛盾  → 改 gold
    反过来——为了让测试通过而补一个下游无人使用的契约字段，
    或因为模型答错就放宽门槛——都是把测试反过来拟合实现。

v1.1：解决 gold_contract_issues 里的 4 项冲突（见下方 CHANGELOG）。
v1.2：v1.1 跑完后 gate 首次 FAIL（risk_score / coordination_cost 各 66.7%），
      逐条核对后确认是同一类缺陷——risk 题的 gold 取值在 prompt 里没有信号。
      契约澄清已生效（pax-risk-high-01 的 irreversibility / impact_scope 由
      0/3 升到 3/3），但 coordination_cost 仍无从推导，补 prompt。

用法：python evals/fix_internal_dataset.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATASET = Path(__file__).resolve().parent / "datasets" / "pax_internal_routing_v1.0.json"

# ---------------------------------------------------------------------------
# 目标态：显式声明，避免"读一遍改一遍"式脚本的幂等性问题
# ---------------------------------------------------------------------------

# 影响范围 2（多模块、多用户、有内部依赖）+ 协调成本 2（同仓库内跨文件、需要 code review）。
# 措辞注意：必须避开契约里的判据关键词。
# 「全用户」是 impact_scope=3 的原文，「跨仓库」是 coordination_cost=3 的原文，
# 写了就等于把答案改成 3。
RISK_MEDIUM_PROMPT = (
    "给系统加一个导出功能，多个业务用户都能把用户列表导出成 Excel 文件，"
    "涉及后端新增一个导出接口和前端新增一个导出按钮，改动都在同一个仓库内，"
    "完成后需要 code review。"
)

# 同上。「多文件和表结构定义」把「跨文件修改」写实，否则协调成本 1 vs 2 无从区分。
RISK_HIGH_PROMPT = (
    "把生产环境账务模块的存量数据迁移到新表结构，涉及 30 张表、约 800 万条历史记录，"
    "需要保留全部历史数据，迁移脚本无法回滚重跑。改动都在账务模块内部，"
    "涉及多个文件和表结构定义的修改，不涉及其他仓库和其他团队。"
)

FINAL_PROMPTS: dict[str, str] = {
    "pax-risk-high-01": RISK_HIGH_PROMPT,
    "pax-risk-medium-01": RISK_MEDIUM_PROMPT,
}

# v1.6：契约 G2 补完后，medium-01 的 irreversibility 从 1 改为 2。
# 依据：题面是「给系统加一个导出功能，后端新增接口 + 前端新增按钮」，
# 属于需要部署上线的改动。补完 G2 后契约明确「改动需要部署上线才能生效的，
# 即使可回滚也至少算 2」，所以 irreversibility=1 不再成立。
# 总分从 7 变 8，risk_level 仍是 medium（7–9 区间）。
# 注意：这不是「看着模型答错改 gold」——模型三次都稳定判 1，改完后这条题会变 0/3，
# 是诚实的结果。改的理由是契约缺口（G2），不是模型表现。
FINAL_DIMS: dict[str, dict[str, int]] = {
    "pax-risk-medium-01": {"irreversibility": 2, "risk_score": 8},
}

FINAL_SECONDARY: dict[str, list[str]] = {
    # 契约对 data_integrity 的定义含「字段错误」；「字段填写后报错说字段不为设定的正则表达式」
    # 是一个字段值校验失败信号。原 gold 漏标。
    "pax-intent-df-01": ["data_integrity"],
}

# 契约 W4 第 254 行原文是 route = ["clarify", "diagnose", "plan", "execute", "review"]，
# 用的是短名。原 gold 写成了 pax-clarify 等全名，偏离了契约自己的记法。
# 模型跟契约抄了 2 次、跟 gold 抄了 1 次，结果 8/9 而不是 3/3 —— 纯粹是记法差异，
# 五个步骤和顺序完全一致。
FINAL_ROUTES: dict[str, list[str]] = {
    "pax-route-df-01": ["clarify", "diagnose", "plan", "execute", "review"],
    "pax-route-fd-01": ["clarify", "plan", "execute", "review"],
    "pax-route-dc-01": ["clarify"],
}

ROUTE_DF_NOTES = (
    "依赖 pax-intent-df-01 的 W1 判定 secondary_intent=['data_integrity']，"
    "因此 W4 的 storage_backend_required 条件成立。两题 prompt 相同，"
    "改动其中一处时必须同步另一处。"
)

REMOVE_FIELDS = ("confidence",)  # 契约 W1–W4 从未定义，下游无任何逻辑读取

CHANGELOG: list[dict] = [
    {
        "version": "1.1",
        "date": "2026-10-02",
        "basis": "results/internal_routing_results.json 的 gold_contract_issues（14 case × 3）",
        "changes": [
            "删除 intent_classification 全部 7 条 gold 的 confidence 字段："
            "契约 W1–W4 从未定义，W2–W4 也没有任何逻辑读取它，是个装饰字段。"
            "为了让测试通过而给契约补一个下游无人使用的字段，等于反向从测试推导契约，方向反了。",
            "pax-risk-high-01 补 prompt 上下文（30 张表 / 800 万行 / 账务 / 无法回滚）："
            "原 prompt「把旧表的数据迁移到新表」无系统级信号，gold 的 impact_scope=3 无法从 prompt "
            "推导，属不可解题。gold 与契约均未改动。",
            "pax-intent-df-01 的 secondary_intent 从 [] 改为 ['data_integrity']，"
            "并给 pax-route-df-01 加 notes 记录依赖："
            "原 gold secondary=[] 让 W4 的 storage_backend_required 条件不成立，"
            "而 gold 要求 true——gold 按契约自身逻辑就是错的（self-contradictory）。",
        ],
        "contract_changes": "skills/pax-orchestrate/SKILL.md 补两条判定边界"
                            "（W1 ux_error 的前端/后端归属、W2 数据类任务的影响范围基准）。",
    },
    {
        "version": "1.2",
        "date": "2026-10-02",
        "basis": "v1.1 跑完（42 次判定）后 gate 首次 FAIL："
                 "risk_score 66.7% / ≥85%、coordination_cost 66.7% / ≥80%、"
                 "category:risk_scoring 66.7% / ≥85%。",
        "changes": [
            "pax-risk-high-01 再补一句「改动都在账务模块内部，不涉及其他仓库和其他团队」："
            "gold 的 coordination_cost=2 需要「模块内跨文件、但非跨仓库/跨团队」这个信号，"
            "原 prompt 完全没有。契约澄清已生效（irreversibility 与 impact_scope 从 0/3 升到 3/3），"
            "但这条维度仍无从推导。",
            "pax-risk-medium-01 补「所有登录用户都能使用 + 后端接口 + 前端按钮 + 需要 code review」："
            "gold 的 coordination_cost=2 同样缺信号。注意 impact_scope=2 没有补——"
            "「用户列表」本身就含多用户信号，契约写的是「多模块、多用户、有内部依赖」，"
            "这一维 gold 是可推导的，模型答错算模型错，不能用补 prompt 掩盖。",
            "pax-risk-low-01 未改动：prompt 是纯解释类问题，四维全 1，模型 3/3 全对。",
        ],
        "gate": "没有放宽任何门槛。gate 的作用是抓这类问题；把门槛调到让数字好看就废了。",
    },
    {
        "version": "1.3",
        "date": "2026-10-02",
        "basis": "v1.2 跑完（42 次判定）后 gate 仍 FAIL：coordination_cost 55.6%、"
                 "impact_scope 77.8%。逐条核对 model reasoning 后发现是**出题人自己的措辞 bug**，"
                 "不是模型错。",
        "changes": [
            "pax-risk-medium-01：v1.2 写的是「所有登录用户都能把用户列表导出」，"
            "而契约里 impact_scope=3 的原文判据就是「全用户」——措辞直接把答案变成了 3，"
            "模型三次一致答 3 是**按契约正确读取**。改成「多个业务用户」（多用户 = 2，不触及全用户）。",
            "pax-risk-medium-01：补「改动都在同一个仓库内」——coordination_cost=3 的判据含「跨仓库操作」，"
            "而「后端接口 + 前端按钮」可被读成跨仓库，原措辞留了这个口子，模型三次都答 3。",
            "pax-risk-high-01：补「涉及多个文件和表结构定义的修改」——协调成本 1 与 2 的区别是"
            "「单人可完成」vs「模块内跨文件修改」，原 prompt 没把「跨文件」写出来，"
            "模型才会偶尔答 1。",
        ],
        "lesson": "补 prompt 时不能碰契约原文里的判据关键词。这一轮之所以能发现，"
                  "正是因为逐条读了 model reasoning 而不是只看分数。",
    },
    {
        "version": "1.4",
        "date": "2026-10-02",
        "basis": "v1.3 跑完（42 次判定）后能力分 95.2%，四项 risk 维度均已 ≥88.9%，"
                 "仅 route 一项 88.9% / ≥90%。逐条比对 expected 与 actual 后发现："
                 "gold 写 ['pax-clarify', 'pax-diagnose', ...]，"
                 "actual 写 ['clarify', 'diagnose', ...]——五个步骤和顺序完全一致。",
        "changes": [
            "三条 route_building 题的 gold 改用契约短名（pax-route-df-01 / pax-route-fd-01 / pax-route-dc-01）。"
            "契约 W4 第 254 行原文就是 route = [\"clarify\", \"diagnose\", ...]，"
            "gold 用全名是 gold 偏离契约，不是模型错。",
            "同时给打分器加了前缀归一化（去 pax- 前缀、小写、去空格），"
            "避免以后同类记法差异再次被当成路由错误。",
        ],
        "note": "外部路由数据集（pax_routing_v1.0.jsonl）不受影响：那里比的是 skill 目录名，"
                "本来就该用 pax-* 全名。两套 gold 的记法基准不同，不矛盾。",
    },
    {
        "version": "1.6",
        "date": "2026-10-03",
        "basis": "D1–D4 四项决策落地后补契约 G1/G2（见 evals/CONTRACT_GAPS.md）。"
                 "G2 的缺口是：契约 1 的示例「代码修改」与 2 的示例「前端部署（可回退）」"
                 "在「新增功能」场景上重叠，两边都能引用契约原文。"
                 "pax-risk-medium-03（holdout）3/3 全错暴露了这个问题；"
                 "静态核对后发现 pax-risk-medium-01 的 gold 也落在同一个缺口里。",
        "changes": [
            "pax-risk-medium-01 的 irreversibility 从 1 改为 2，risk_score 从 7 改为 8"
            "（risk_level 仍是 medium，7–9 区间不变）。"
            "依据：补完 G2 后契约明确「改动需要部署上线才能生效的，即使可回滚也至少算 2」，"
            "而题面「后端新增导出接口 + 前端新增导出按钮」是需要部署的改动。",
            "★ 这不是「看着模型答错改 gold」：模型三次都稳定判 1，改完后这条题会变成 0/3，"
            "是诚实的结果。改的理由是契约缺口，不是模型表现；方向是「更严格」不是「凑分」。",
            "影响评估：改完后 risk_scoring 从 6/20 降到 5/20（-1），总分 46/52 → 45/52。"
            "这个下降是预期的——gold 跟上了契约，不再用「代码修改」这个过宽示例兜底。",
        ],
        "contract_changes": "skills/pax-orchestrate/SKILL.md 的 W2 不可逆性与影响范围判据："
                           "G1 给「内部工具」加「仅本人使用」限定；"
                           "G2 给「代码修改」加「未上线的本地改动」限定、"
                           "给「配置修改」加「不触发部署」限定，"
                           "并把 2 的示例改为「前端/后端部署（可回退）」；两条都补了显式边界说明。",
        "holdout_integrity": "G1/G2 补完后 pax-risk-medium-03（holdout 锁定题）的 prompt 与 gold 不变。"
                             "impact_scope=2 现在有明确契约依据（内部工具按使用人数判定）；"
                             "FAIL 归因从「契约缺口」转为「模型是否跟上新契约」，重跑后见分晓。",
    },
]


def main() -> int:
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = raw["cases"]
    log: list[str] = []

    for c in cases:
        cid, exp = c["id"], c["expected"]

        for f in REMOVE_FIELDS:
            if f in exp:
                exp.pop(f)
                log.append(f"{cid}: 删除 {f}")

        if cid in FINAL_SECONDARY and exp.get("secondary_intent") != FINAL_SECONDARY[cid]:
            log.append(f"{cid}: secondary_intent {exp.get('secondary_intent')} → "
                       f"{FINAL_SECONDARY[cid]}")
            exp["secondary_intent"] = FINAL_SECONDARY[cid]

        if cid in FINAL_ROUTES and exp.get("route") != FINAL_ROUTES[cid]:
            log.append(f"{cid}: route 改用契约短名 {exp.get('route')} → {FINAL_ROUTES[cid]}")
            exp["route"] = FINAL_ROUTES[cid]

        if cid in FINAL_DIMS:
            for k, v in FINAL_DIMS[cid].items():
                if exp.get(k) != v:
                    log.append(f"{cid}: {k} {exp.get(k)} → {v}（v1.6，契约 G2 补完后 gold 跟进）")
                    exp[k] = v

        if cid in FINAL_PROMPTS and c["prompt"] != FINAL_PROMPTS[cid]:
            log.append(f"{cid}: prompt 补齐推导信号\n    前：{c['prompt']}\n    后：{FINAL_PROMPTS[cid]}")
            c["prompt"] = FINAL_PROMPTS[cid]

        if cid == "pax-route-df-01" and c.get("notes") != ROUTE_DF_NOTES:
            c["notes"] = ROUTE_DF_NOTES
            log.append(f"{cid}: 增加 notes，记录对 pax-intent-df-01 W1 判定的依赖")

    raw["version"] = "1.6"
    # changelog 合并而非覆盖：add_holdout_cases.py 追加的 v1.5 条目不能丢
    by_ver: dict[str, dict] = {e.get("version", ""): e for e in raw.get("changelog", [])}
    for entry in CHANGELOG:
        by_ver[entry["version"]] = entry
    raw["changelog"] = [by_ver[k] for k in sorted(
        (v for v in by_ver.keys() if v),
        key=lambda v: tuple(int(x) for x in v.split(".")))]
    DATASET.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"数据集 → v1.6\n")
    if log:
        for line in log:
            print(" ", line)
    else:
        print("  （已是目标态，无需改动）")

    # 自检
    errs: list[str] = []
    for c in cases:
        if any(f in c["expected"] for f in REMOVE_FIELDS):
            errs.append(f"{c['id']}: 残留 {REMOVE_FIELDS}")
        if c["id"] in FINAL_PROMPTS and c["prompt"] != FINAL_PROMPTS[c["id"]]:
            errs.append(f"{c['id']}: prompt 未生效")
        if c["id"] in FINAL_SECONDARY and c["expected"]["secondary_intent"] != FINAL_SECONDARY[c["id"]]:
            errs.append(f"{c['id']}: secondary_intent 未生效")
        if c["id"] in FINAL_ROUTES and c["expected"]["route"] != FINAL_ROUTES[c["id"]]:
            errs.append(f"{c['id']}: route 未生效")
        if c["id"] in FINAL_DIMS and any(
                c["expected"].get(k) != v for k, v in FINAL_DIMS[c["id"]].items()):
            errs.append(f"{c['id']}: 四维值未生效")

    # 每条 risk 题的四维加起来必须等于 gold 的 risk_score，且映射到正确的 risk_level。
    # 注意：必须考虑 W2 的强制升级规则，否则高分类题会被误判为 gold 错。
    # 强制升级规则：security 二级意图 / data_integrity+impact 3 / 不可逆3+影响3 → high
    for c in cases:
        if c["category"] != "risk_scoring":
            continue
        exp = c["expected"]
        total = sum(exp[k] for k in ("irreversibility", "impact_scope", "uncertainty", "coordination_cost"))
        if total != exp["risk_score"]:
            errs.append(f"{c['id']}: 四维和 {total} ≠ risk_score {exp['risk_score']}")
        band = "low" if total <= 6 else ("medium" if total <= 9 else "high")
        secs = exp.get("secondary_intent") or []
        # 二级意图在 risk_scoring 题里不一定有，有才判
        forced = (
            "security" in secs
            or ("data_integrity" in secs and exp["impact_scope"] == 3)
            or (exp["irreversibility"] == 3 and exp["impact_scope"] == 3)
        )
        expected_level = "high" if forced else band
        if expected_level != exp["risk_level"]:
            why = "强制升级" if forced else "总分映射"
            errs.append(f"{c['id']}: 总分 {total} 经{why}应为 {expected_level}，gold 是 {exp['risk_level']}")

    print(f"\n共 {len(cases)} 条 case，{len(log)} 处改动")
    if errs:
        print("✗ 自检失败：")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("✓ 自检通过（confidence 已清空 / prompt 与 secondary 已生效 / 四维求和与等级映射自洽）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
