#!/usr/bin/env python3
"""向内部路由数据集追加 v2 扩题（25 题），数据集 v1.7。

为什么需要这个脚本

v1.6 的 18 题覆盖严重不足：security/ux_error/integration/deployment 四种
二级意图完全未测；强制升级规则 data_integrity+imp=3→high 未实测；W3 强制
诊断 feature_dev+security→diagnose=true 未测；risk 维度分 5/11/12 缺。

本脚本追加 25 题，覆盖这些空白。全部标记 holdout（gold 一次性推导，写入后
不修订，与 add_holdout_cases.py 的 4 条锁定题同规则）。

与 add_holdout_cases.py 的分工

add_holdout_cases.py 管理 v1.5 追加的 4 条 risk_scoring 锁定题。本脚本管理
v1.7 追加的 25 题（intent/risk/route/cross_repo 四类）。两个脚本的 case id
不重叠，各自 --check 各自的题。

锁定规则（与 add_holdout_cases.py 相同）

1. gold 在写入前按契约推导完成，写入后不再修改 prompt，也不再修改 gold。
2. 模型答错 → 如实记 FAIL，不做任何修订。
3. 唯一的例外：如果复核发现 gold 与契约原文直接矛盾，可以改，但必须在
   changelog 里写明「这是契约矛盾，不是拟合」。
4. 题面里不出现会替我下结论的暗示词。gold 必须能仅凭 prompt + 契约文字推导。

强制升级规则自检

pax-risk-high-04：维度分 2+3+2+2=9（本该 medium），但 prompt 含 data_integrity
信号且 imp=3 → 强制 high。gold risk_level=high。
pax-risk-high-05：维度分 1+3+1+1=6（本该 low），但 prompt 含 data_integrity
信号且 imp=3 → 强制 high。gold risk_level=high。

用法：
    python evals/add_v2_cases.py            # 追加并校验
    python evals/add_v2_cases.py --check    # 只校验，不改文件
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATASET = Path(__file__).resolve().parent / "datasets" / "pax_internal_routing_v1.0.json"
NEW_VERSION = "1.7"

CHANGELOG_ENTRY = {
    "version": "1.7",
    "date": "2026-10-03",
    "summary": "追加 25 题 v2 扩题（全部 holdout），覆盖现有 18 题的空白区：",
    "basis": "覆盖分析见 evals/DESIGN_V2_CASES.md。5 项边界裁决已由用户确认。",
    "changes": [
        "intent_classification +9：security/ux_error/integration/deployment 首次覆盖，",
        "  多 secondary 叠加（performance+data_integrity），feature_dev+security 强制诊断。",
        "risk_scoring +8：维度分 5/6/7 补全；强制升级 data_integrity+imp=3→high 首次实测",
        "  （high-04 维度9→high, high-05 维度6→high）；irr=3+imp=3→high 补一题（high-03）。",
        "route_building +5：security/ux_error/data_ops/refactor/feature_dev+security 强制诊断。",
        "cross_repo_detection +3：微服务跨服务、同仓库（false）、已知仓库名。",
        "25 题全部标记 holdout，与 v1.5 的 4 条锁定题同规则（写入后不修订）。",
        "数据集从 18 题扩到 43 题。",
    ],
    "note": "本批 gold 一次性按契约推导，未参考模型输出。模型答错如实记 FAIL。",
}

V2_CASES: list[dict] = [
    # ── intent_classification +9 ──────────────────────────────────────────
    {
        "id": "pax-intent-ds-01", "category": "intent_classification", "holdout": True,
        "prompt": "生产环境发现一个 SQL 注入漏洞，用户输入直接拼接到查询语句里，攻击者可以通过特殊字符绕过认证。需要立即修复，防止数据泄露。",
        "expected": {"primary_intent": "diagnose_fix", "secondary_intent": ["security"]},
    },
    {
        "id": "pax-intent-ux-01", "category": "intent_classification", "holdout": True,
        "prompt": "用户在网页上点击提交按钮没有任何反应，控制台显示一个 JS 错误，但后端接口其实返回了正常数据。",
        "expected": {"primary_intent": "diagnose_fix", "secondary_intent": ["ux_error"]},
    },
    {
        "id": "pax-intent-ig-01", "category": "intent_classification", "holdout": True,
        "prompt": "调用第三方支付接口返回 500 错误，对方说他们的服务正常，我们这边请求格式可能有问题。",
        "expected": {"primary_intent": "diagnose_fix", "secondary_intent": ["integration"]},
    },
    {
        "id": "pax-intent-de-01", "category": "intent_classification", "holdout": True,
        "prompt": "昨天部署到生产环境后，新版本的配置没有生效，所有用户都看到了旧版本的页面。部署脚本执行成功了，但配置项没被读取。",
        "expected": {"primary_intent": "diagnose_fix", "secondary_intent": ["deployment"]},
    },
    {
        "id": "pax-intent-dpi-01", "category": "intent_classification", "holdout": True,
        "prompt": "最近一周系统响应时间从 200ms 增加到 2s，同时发现数据库里有一些订单状态不一致，部分订单在业务系统显示已完成但数据库里还是 pending。",
        "expected": {"primary_intent": "diagnose_fix", "secondary_intent": ["performance", "data_integrity"]},
    },
    {
        "id": "pax-intent-do-02", "category": "intent_classification", "holdout": True,
        "prompt": "需要把用户表里所有 status 为 0 的记录批量更新为 1，这些是测试数据，共约 200 条。",
        "expected": {"primary_intent": "data_ops", "secondary_intent": []},
    },
    {
        "id": "pax-intent-fs-01", "category": "intent_classification", "holdout": True,
        "prompt": "给系统加一个管理员后台，管理员可以查看和修改所有用户的个人信息，包括身份证号和手机号。",
        "expected": {"primary_intent": "feature_dev", "secondary_intent": ["security"]},
    },
    {
        "id": "pax-intent-rp-01", "category": "intent_classification", "holdout": True,
        "prompt": "用户列表查询接口在数据量超过 10 万条时很慢，需要优化查询逻辑，加索引或改分页策略，但不改变接口的入参和出参。",
        "expected": {"primary_intent": "refactor", "secondary_intent": ["performance"]},
    },
    {
        "id": "pax-intent-ti-01", "category": "intent_classification", "holdout": True,
        "prompt": "写一个脚本，定时从公司内部的 GitLab API 拉取代码提交记录，汇总成日报发送到飞书群。",
        "expected": {"primary_intent": "tool_build", "secondary_intent": ["integration"]},
    },

    # ── risk_scoring +8 ───────────────────────────────────────────────────
    {
        "id": "pax-risk-low-03", "category": "risk_scoring", "holdout": True,
        "prompt": "把团队内部的一个共享脚本里的日志格式从纯文本改成 JSON，方便机器解析。团队内 3 个人会用这个脚本，改动后本地覆盖旧版本即可，不需要部署。改动很明确，就是把 print 改成 json.dumps。",
        "expected": {"irreversibility": 1, "impact_scope": 2, "uncertainty": 1, "coordination_cost": 1, "risk_score": 5, "risk_level": "low"},
    },
    {
        "id": "pax-risk-low-04", "category": "risk_scoring", "holdout": True,
        "prompt": "在本地开发环境试一下用 Redis 替代内存缓存，写个原型验证性能差异。改动只在我的开发分支上，不影响任何生产数据。没用过 Redis 客户端库，需要先看一下文档。",
        "expected": {"irreversibility": 1, "impact_scope": 1, "uncertainty": 2, "coordination_cost": 1, "risk_score": 5, "risk_level": "low"},
    },
    {
        "id": "pax-risk-low-05", "category": "risk_scoring", "holdout": True,
        "prompt": "把本地开发环境的 Node.js 版本从 18 升到 20，改一下 package.json 的 engines 字段。改完需要重新部署到开发服务器，但可以一键回退到旧版本。需求很明确，不涉及生产环境，只有我一个人用这个开发环境。",
        "expected": {"irreversibility": 2, "impact_scope": 1, "uncertainty": 1, "coordination_cost": 1, "risk_score": 5, "risk_level": "low"},
    },
    {
        "id": "pax-risk-low-06", "category": "risk_scoring", "holdout": True,
        "prompt": "给团队共享的内部工具加一个数据导出功能，团队内 5 个人会用。导出格式用 CSV 还是 Excel 还没确定，需要先跟产品经理确认。改动在工具内部，本地覆盖旧版本即可。",
        "expected": {"irreversibility": 1, "impact_scope": 2, "uncertainty": 2, "coordination_cost": 1, "risk_score": 6, "risk_level": "low"},
    },
    {
        "id": "pax-risk-medium-04", "category": "risk_scoring", "holdout": True,
        "prompt": "把用户注册接口从 HTTP 升级到 HTTPS，需要配置 SSL 证书。接口有 3 个调用方（都在同一个仓库内）。证书配置流程不熟，需要先查文档验证一轮。改动由我一个人完成，不需要 code review。",
        "expected": {"irreversibility": 2, "impact_scope": 2, "uncertainty": 2, "coordination_cost": 1, "risk_score": 7, "risk_level": "medium"},
    },
    {
        "id": "pax-risk-medium-05", "category": "risk_scoring", "holdout": True,
        "prompt": "删除生产数据库中已过期 1 年的测试环境数据备份（非生产数据），物理删除无法恢复。这些备份只有测试团队内部使用。删除操作有标准手册，我一个人执行即可。",
        "expected": {"irreversibility": 3, "impact_scope": 2, "uncertainty": 1, "coordination_cost": 1, "risk_score": 7, "risk_level": "medium"},
    },
    {
        "id": "pax-risk-high-03", "category": "risk_scoring", "holdout": True,
        "prompt": "把生产数据库的用户表从 MySQL 迁移到 PostgreSQL，涉及用户表、订单表、支付记录表共 8 张表的关联迁移，数据量约 2000 万行。迁移后需要验证数据一致性，有回滚脚本但回滚需要重新导入全量数据。涉及后端和前端两个团队的协调。",
        "expected": {"irreversibility": 3, "impact_scope": 3, "uncertainty": 2, "coordination_cost": 3, "risk_score": 11, "risk_level": "high"},
    },
    {
        "id": "pax-risk-high-04", "category": "risk_scoring", "holdout": True,
        "prompt": "生产环境中发现订单状态与支付状态不一致，部分用户已支付但订单仍显示待支付。需要排查不一致的原因并批量订正，涉及订单表、支付表、用户表共 3 张表的数据修复，影响所有用户。修复方案需要先验证一轮再上线，改动涉及后端和前端两个模块，需要 code review。",
        "expected": {"irreversibility": 2, "impact_scope": 3, "uncertainty": 2, "coordination_cost": 2, "risk_score": 9, "risk_level": "high"},
    },
    {
        "id": "pax-risk-high-05", "category": "risk_scoring", "holdout": True,
        "prompt": "生产环境的用户登录日志表里，有部分记录的 login_time 字段是空值，导致报表统计时出现 NULL 错误。需要排查原因并批量填充这些空值。涉及所有用户的历史登录记录，数据量约 5000 万行。操作前有完整备份，按标准流程执行，我一个人完成即可。",
        "expected": {"irreversibility": 1, "impact_scope": 3, "uncertainty": 1, "coordination_cost": 1, "risk_score": 6, "risk_level": "high"},
    },

    # ── route_building +5 ─────────────────────────────────────────────────
    {
        "id": "pax-route-ds-01", "category": "route_building", "holdout": True,
        "prompt": "生产环境发现一个 SQL 注入漏洞，用户输入直接拼接到查询语句里，攻击者可以通过特殊字符绕过认证。需要立即修复。",
        "expected": {"route": ["clarify", "diagnose", "plan", "execute", "review"], "diagnose_required": True, "storage_backend_required": False},
    },
    {
        "id": "pax-route-ux-01", "category": "route_building", "holdout": True,
        "prompt": "用户在网页上点击提交按钮没有任何反应，控制台显示一个 JS 错误，但后端接口其实返回了正常数据。",
        "expected": {"route": ["clarify", "diagnose", "plan", "execute", "review"], "diagnose_required": True, "storage_backend_required": False},
    },
    {
        "id": "pax-route-do-02", "category": "route_building", "holdout": True,
        "prompt": "需要把用户表里所有 status 为 0 的记录批量更新为 1，这些是测试数据，共约 200 条。",
        "expected": {"route": ["clarify", "diagnose", "plan", "execute", "review"], "diagnose_required": True, "storage_backend_required": True},
    },
    {
        "id": "pax-route-rf-01", "category": "route_building", "holdout": True,
        "prompt": "把 500 行的单体方法拆分成多个职责单一的函数，保持接口行为不变。",
        "expected": {"route": ["clarify", "plan", "execute", "review"], "diagnose_required": False, "storage_backend_required": False},
    },
    {
        "id": "pax-route-fs-01", "category": "route_building", "holdout": True,
        "prompt": "给系统加一个管理员后台，管理员可以查看和修改所有用户的个人信息，包括身份证号和手机号。",
        "expected": {"route": ["clarify", "diagnose", "plan", "execute", "review"], "diagnose_required": True, "storage_backend_required": False},
    },

    # ── cross_repo_detection +3 ───────────────────────────────────────────
    {
        "id": "pax-cross-repo-02", "category": "cross_repo_detection", "holdout": True,
        "prompt": "订单服务需要调用用户服务的新接口来获取用户偏好信息，两个服务部署在不同的服务器上。",
        "expected": {"cross_repo": True, "execution_strategy_required": True},
    },
    {
        "id": "pax-cross-repo-03", "category": "cross_repo_detection", "holdout": True,
        "prompt": "在同一个仓库内，服务 A 需要调用服务 B 的新函数，两个服务在同一个代码仓库里。",
        "expected": {"cross_repo": False, "execution_strategy_required": False},
    },
    {
        "id": "pax-cross-repo-04", "category": "cross_repo_detection", "holdout": True,
        "prompt": "前端 React 项目需要调用后端 Express 项目的新接口，两个项目分别在 ops-pilot-web 和 ops-monitor 两个仓库中。",
        "expected": {"cross_repo": True, "execution_strategy_required": True},
    },
]


def _self_check() -> list[str]:
    """强制升级规则与总分一致性自检。"""
    errs: list[str] = []
    for c in V2_CASES:
        e = c["expected"]
        if c["category"] != "risk_scoring":
            continue
        dims = [e["irreversibility"], e["impact_scope"], e["uncertainty"], e["coordination_cost"]]
        total = sum(dims)
        if total != e["risk_score"]:
            errs.append(f'{c["id"]}: 维度分 {dims}={total} != risk_score {e["risk_score"]}')
        # 总分映射
        expected_level = "low" if total <= 6 else "medium" if total <= 9 else "high"
        # 强制升级：data_integrity + imp=3 → high；irr=3 + imp=3 → high
        forced = False
        if e["impact_scope"] == 3:
            # data_integrity 信号检测（prompt 含数据不一致/字段错误等）
            p = c["prompt"]
            if any(k in p for k in ["不一致", "空值", "脏数据", "数据丢失"]):
                forced = True  # data_integrity + imp=3
            if e["irreversibility"] == 3:
                forced = True  # irr=3 + imp=3
        if forced and e["risk_level"] != "high":
            errs.append(f'{c["id"]}: 应强制升级 high，但 gold={e["risk_level"]}')
        if not forced and e["risk_level"] != expected_level:
            errs.append(f'{c["id"]}: 无强制升级，维度分 {total} 应映射 {expected_level}，但 gold={e["risk_level"]}')
        # 维度范围
        for f in ["irreversibility", "impact_scope", "uncertainty", "coordination_cost"]:
            if not 1 <= e[f] <= 3:
                errs.append(f'{c["id"]}: {f}={e[f]} 超出 1-3')
    return errs


def add_cases(check_only: bool) -> int:
    errs = _self_check()
    if errs:
        print("ERROR: 自检失败：")
        for e in errs:
            print(f"  - {e}")
        return 1

    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    existing = {c["id"] for c in raw["cases"]}
    todo = [c for c in V2_CASES if c["id"] not in existing]

    if check_only:
        holdouts = [c["id"] for c in raw["cases"] if c.get("holdout")]
        print(f"数据集 v{raw.get('version')}，共 {len(raw['cases'])} 题，holdout {len(holdouts)} 题")
        missing = [c["id"] for c in V2_CASES if c["id"] not in existing]
        print(f"待追加：{[c['id'] for c in todo] if todo else '无'}")
        if missing:
            print("ERROR: 锁定题缺失：" + ", ".join(missing))
            return 1
        # 锁定校验
        drift = []
        for c in V2_CASES:
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
        print(f"数据集 v{raw['version']}：25 条 v2 题已全部存在，无需追加。")
        if raw.get("version") != NEW_VERSION:
            raw["version"] = NEW_VERSION
            raw["changelog"].append(CHANGELOG_ENTRY)
            DATASET.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"仅补齐 version 字段：→ v{NEW_VERSION}")
        return 0

    raw["cases"].extend(todo)
    raw["version"] = NEW_VERSION
    raw["changelog"].append(CHANGELOG_ENTRY)
    DATASET.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"数据集 v1.6 → v{NEW_VERSION}")
    for c in todo:
        e = c["expected"]
        cat = c["category"]
        if cat == "risk_scoring":
            dims = [e["irreversibility"], e["impact_scope"], e["uncertainty"], e["coordination_cost"]]
            print(f"  + {c['id']}  ({','.join(map(str,dims))}={sum(dims)}) → {e['risk_level']}")
        elif cat == "intent_classification":
            print(f"  + {c['id']}  {e['primary_intent']} + {e['secondary_intent']}")
        elif cat == "route_building":
            print(f"  + {c['id']}  diag={e['diagnose_required']} storage={e['storage_backend_required']}")
        else:
            print(f"  + {c['id']}  cross={e['cross_repo']}")
    print(f"\n共 {len(raw['cases'])} 题，holdout {sum(1 for c in raw['cases'] if c.get('holdout'))} 题（锁定，不再修订）")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="只校验锁定题是否存在且未漂移，不改文件")
    sys.exit(add_cases(ap.parse_args().check))
