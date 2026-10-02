#!/usr/bin/env python3
"""向内部路由数据集追加「锁定泛化题」（holdout），数据集 v1.5。

为什么需要这个脚本

内部路由评估从 v1.0 修到 v1.4，改过 6 处 gold，其中至少 4 处是我**看着模型答错之后**
才去核对契约、发现 gold 有问题。也就是说数据集被「反拟合」过模型行为：
模型答错的题，我倾向于回头修数据集而不是承认失败。

这样得到的 100% 不是无偏估计。要判断它是不是虚高，需要一批**从未被修订过**的题，
看模型在完全陌生的题面上还能不能拿高分。

锁定规则（本脚本的存在就是为了把这条规则写死）

1. gold 在写入前按契约推导完成，写入后**不再修改 prompt，也不再修改 gold**。
2. 模型答错 → 如实记 FAIL，不做任何修订。
3. 唯一的例外：如果复核发现 gold **与契约原文直接矛盾**（而不是「模型没读懂我的
   措辞」），可以改，但必须在 changelog 里写明「这是契约矛盾，不是拟合」。
4. 题面里不出现会替我下结论的暗示词。gold 必须能仅凭 prompt + 契约文字推导。

与 fix_internal_dataset.py 的分工

fix_internal_dataset.py 是针对特定 case_id 的**定向修订**脚本，处理的是「历史题
gold 与契约冲突」这类已确认的问题。本脚本只做**追加**，不碰已有 case，
两个脚本的改动范围不重叠。

用法：
    python evals/add_holdout_cases.py            # 追加并校验
    python evals/add_holdout_cases.py --check    # 只校验，不改文件
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATASET = Path(__file__).resolve().parent / "datasets" / "pax_internal_routing_v1.0.json"
NEW_VERSION = "1.5"

# ---------------------------------------------------------------------------
# 4 条新题。每条的 gold 都是按契约推导出来的，推导依据写在 notes 里，便于审计。
# 现有 3 条 risk 题的四维组合是 (3,3,2,2) / (1,2,2,2) / (1,1,1,1)，
# 下面 4 条刻意选了不重复的组合，并且每条考一个不同的点。
# ---------------------------------------------------------------------------

HOLDOUT_CASES: list[dict] = [
    {
        "id": "pax-risk-low-02",
        "category": "risk_scoring",
        "holdout": True,
        "prompt": (
            "调整内部数据导出脚本的一个配置项，把导出的时间窗口从 7 天改成 30 天。"
            "改动前脚本有备份，改错了可以直接还原。这个脚本财务和运营两个组每周各用一次。"
            "需求明确，就是把窗口参数改掉，没有其他改动。改动都在同一个团队内部，"
            "涉及 2 个文件，需要走一次 code review。"
        ),
        "expected": {
            "irreversibility": 1,   # 有备份可直接还原 → 契约 1 示例「配置修改（有备份）」
            "impact_scope": 2,      # 财务+运营两组使用 = 多用户；非仅本人 → 非 1；未达主链路 → 非 3
            "uncertainty": 1,       # 需求明确、只改一个参数 → 契约 1「需求明确、方案清晰」
            "coordination_cost": 2,  # 2 个文件 + code review → 契约 2「跨文件…需要 code review」
            "risk_score": 6,        # 1+2+1+2
            "risk_level": "low",    # 6 落在 4–6
        },
        "notes": (
            "考 low 的上限边界（6 vs 7）。四维里只有 uncertainty 是 1，其余都是 2，"
            "任何一维被高估一分就翻到 medium。写「同一个团队内部」是为了排掉"
            "跨团队 → 协调成本 3 的歧义。"
        ),
    },
    {
        "id": "pax-risk-medium-02",
        "category": "risk_scoring",
        "holdout": True,
        "prompt": (
            "把商品详情查询接口从同步调用改成异步。这个接口是所有客户下单前必经的查询入口，"
            "涉及团队内 3 个服务的调用改造，改动都在同一个仓库内。"
            "上线后有回滚脚本可以切回同步模式。调用顺序需要在测试环境验证一轮再上线，"
            "改动完成后需要走一次 code review。"
        ),
        "expected": {
            "irreversibility": 2,   # 有回滚脚本 → 契约 2「数据库迁移（有 down 脚本）」同类
            "impact_scope": 3,      # 「所有客户下单前必经」= 全用户 → 契约 3
            "uncertainty": 2,       # 调用顺序需验证 → 契约 2「需要验证假设」
            "coordination_cost": 2,  # 同一仓库 + code review；「团队内」排掉跨团队
            "risk_score": 9,        # 2+3+2+2
            "risk_level": "medium",  # 9 落在 7–9
        },
        "notes": (
            "考 medium 的上限边界（9 vs 10）和 impact_scope=3 的「全用户」判定。"
            "特意不写「账务/支付/数据完整性」这类词——契约里 data_integrity+impact3 会"
            "强制升到 high，会污染这条题要考的点。写「团队内」「同一个仓库」是为了"
            "排掉协调成本 3 的歧义。"
        ),
    },
    {
        "id": "pax-risk-high-02",
        "category": "risk_scoring",
        "holdout": True,
        "prompt": (
            "清理生产数据库中 3 年前的过期订单记录，物理删除无法恢复，"
            "涉及公司所有用户的订单历史。这是标准的数据清理流程，公司有明确的清理脚本和"
            "操作手册，由我单人执行即可，不需要其他人配合。"
        ),
        "expected": {
            "irreversibility": 3,   # 物理删除无法恢复 → 契约 3 示例「数据删除/覆盖」
            "impact_scope": 3,      # 公司所有用户 → 契约 3「全用户」
            "uncertainty": 1,       # 标准流程、有脚本和手册 → 契约 1「有先例可循」
            "coordination_cost": 1,  # 单人执行、不需要配合 → 契约 1「单人可完成」
            "risk_score": 8,        # 3+3+1+1
            "risk_level": "high",    # 总分 8 本应 medium；不可逆性3 + 影响范围3 → 强制 high
        },
        "notes": (
            "★ 这批题里唯一能测出「强制升级规则有没有被真的应用」的一条。"
            "四维加起来是 8，按总分映射表（4–6 低 / 7–9 中 / 10–12 高）应该是 medium，"
            "但契约 W2 明确写了「不可逆性为 3 且影响范围为 3 → 强制 risk: high」。"
            "现有 3 条题测不出这一点：pax-risk-high-01 总分 10 本来就是 high，"
            "强制升级不改变结果。模型如果只按总分映射作答就会答 medium → FAIL。"
            "这条 FAIL 是契约应用缺陷，不是数据集问题。"
        ),
    },
    {
        "id": "pax-risk-medium-03",
        "category": "risk_scoring",
        "holdout": True,
        "prompt": (
            "把内部运营后台的订单列表页筛选组件从旧版换成新版组件库的组件，"
            "改动涉及运营模块的 3 个文件，上线后可以一键切回旧版组件。"
            "组件交互细节需要先确认一次需求，确认后改动由我一个人完成，不需要其他人配合。"
        ),
        "expected": {
            "irreversibility": 2,   # 可回滚但需要步骤（切回旧版）→ 契约 2「前端部署（可回退）」
            "impact_scope": 2,      # 内部运营人员使用 = 多用户但非全用户 → 契约 2
            "uncertainty": 2,       # 交互细节需先确认 → 契约 2「部分需求未明确」
            "coordination_cost": 1,  # 单人完成 → 契约 1「单人可完成、无需协调」
            "risk_score": 7,        # 2+2+2+1
            "risk_level": "medium",  # 7 落在 7–9
        },
        "notes": (
            "考「单人可完成」但仍有中风险的情形——现有题的协调成本最低是 1（low-01，"
            "四维全 1），最高是 2，没有「协调成本 1 但总分 7」的组合。"
            "写「内部运营后台」是为了排掉全用户 → impact 3 的歧义；"
            "写「确认后由我一个人完成」是为了让协调成本明确落在 1。"
        ),
    },
]

CHANGELOG_ENTRY = {
    "version": "1.5",
    "date": "2026-10-02",
    "basis": (
        "v1.0 → v1.4 改过 6 处 gold，其中至少 4 处是看着模型答错之后才核对契约、"
        "发现 gold 有问题。3 条 risk 题里有 2 条（high-01、medium-01）的 prompt 被改过，"
        "所以「1–3 主观量纲是契约实现最弱的部分」这个判断没有任何一条从未修订过的题支撑。"
    ),
    "changes": [
        "追加 4 条 risk_scoring 锁定题（holdout），四维组合与现有 3 条不重复：",
        "  - pax-risk-low-02    (1,2,1,2) = 6  low    考 low 上限边界（6 vs 7）",
        "  - pax-risk-medium-02 (2,3,2,2) = 9  medium 考 medium 上限边界（9 vs 10）+ 全用户判定",
        "  - pax-risk-high-02   (3,3,1,1) = 8  high   考强制升级规则：总分 8 本应 medium，",
        "    但不可逆性3+影响范围3 强制升到 high——唯一能测出该规则是否被应用的题",
        "  - pax-risk-medium-03 (2,2,2,1) = 7  medium 考协调成本 1 的中风险组合",
        "case 增加 holdout 标记，评估脚本按此分组统计。",
    ],
    "note": (
        "★ 锁定规则：这 4 条题的 prompt 与 gold 写入后不再修订。模型答错如实记 FAIL。"
        "唯一例外是复核发现 gold 与契约原文直接矛盾（而非「模型没读懂措辞」），"
        "且必须在 changelog 里写明「这是契约矛盾，不是拟合」。"
        "与 fix_internal_dataset.py 的区别：那个脚本是针对历史题的定向修订，"
        "本脚本只追加，不碰已有 case。"
    ),
}


def add_cases(check_only: bool) -> int:
    """把 HOLDOUT_CASES 追加进数据集。幂等：已存在同 id 的 case 则跳过。"""
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    existing = {c["id"] for c in raw["cases"]}

    todo = [c for c in HOLDOUT_CASES if c["id"] not in existing]

    if check_only:
        holdouts = [c["id"] for c in raw["cases"] if c.get("holdout")]
        print(f"数据集 v{raw.get('version')}，共 {len(raw['cases'])} 题，holdout {len(holdouts)} 题")
        missing = [c["id"] for c in HOLDOUT_CASES if c["id"] not in existing]
        print(f"待追加：{todo and [c['id'] for c in todo] or '无'}")
        if missing:
            print("ERROR: 锁定题缺失：" + ", ".join(missing))
            return 1
        # 锁定校验：holdout 题的 expected 必须与脚本里写死的值一致
        drift = []
        for c in HOLDOUT_CASES:
            cur = next((x for x in raw["cases"] if x["id"] == c["id"]), None)
            if cur is None:
                continue
            if cur["expected"] != c["expected"] or cur["prompt"] != c["prompt"]:
                drift.append(c["id"])
        if drift:
            print("ERROR: 锁定题已被修改（违反锁定规则）：" + ", ".join(drift))
            return 1
        print("锁定题与脚本写死的值一致，未漂移。")
        return 0

    if not todo:
        print(f"数据集 v{raw['version']}：4 条锁定题已全部存在，无需追加。")
        if raw.get("version") != NEW_VERSION:
            raw["version"] = NEW_VERSION
            raw["changelog"].append(CHANGELOG_ENTRY)
            DATASET.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
            print(f"仅补齐 version 字段：→ v{NEW_VERSION}")
        return 0

    raw["cases"].extend(todo)
    raw["version"] = NEW_VERSION
    raw["changelog"].append(CHANGELOG_ENTRY)
    DATASET.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"数据集 v{raw['changelog'][0]['version']} → v{NEW_VERSION}")
    for c in todo:
        e = c["expected"]
        dims = [e["irreversibility"], e["impact_scope"], e["uncertainty"], e["coordination_cost"]]
        total = sum(dims)
        print(f"  + {c['id']}  四维 {dims} = {total}  → {e['risk_level']}")
    print(f"\n共 {len(raw['cases'])} 题，holdout {len(todo)} 题（锁定，不再修订）")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="只校验锁定题是否存在且未漂移，不改文件")
    sys.exit(add_cases(ap.parse_args().check))
