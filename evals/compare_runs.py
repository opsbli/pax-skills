#!/usr/bin/env python3
"""对比两次 skillEval routing 运行的逐 case 表现（A/B 分析）。

用途：v2.0 基线与 description 对照组之间的差异归因。也适用于任何两次同数据集、
不同 skill 集（或不同模型）的 routing 运行对比。

只读 runs.jsonl / scores.json + 数据集 gold，不调 API、不写盘。

用法
----
    PY=../agent-skills-tooling/skillEval/.venv/Scripts/python.exe

    # 直接给两个 run 目录
    $PY evals/compare_runs.py <run_dir_a> <run_dir_b> --label-a v2.0 --label-b 对照组

    # 省略数据集则自动从 case_id 前缀推断类型（pax-pos-* / pax-amb-* / ...）
    $PY evals/compare_runs.py <a> <b> --dataset evals/datasets/pax_routing_v1.0.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

CASE_FIELDS = ("case_id", "repeat_index", "selected_skills")
GOLD_FIELDS = ("expected_skills", "expected", "gold")


def _gold_key(d: dict) -> str:
    for k in GOLD_FIELDS:
        if k in d:
            return k
    raise SystemExit("数据集行里找不到 gold 字段（期望 %s）" % (GOLD_FIELDS,))


def load_dataset(path: str | None) -> dict[str, tuple]:
    """case_id -> gold 选择集合。jsonl 允许 `#` 注释头。"""
    if not path:
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        o = json.loads(line)
        key = _gold_key(o)
        out[o.get("id") or o.get("case_id")] = tuple(o[key])
    return out


def load_runs(run_dir: str, gold: dict[str, tuple]) -> dict[str, list]:
    """case_id -> [(selected, gold), ...]，按 repeat_index 排序。"""
    p = Path(run_dir) / "runs.jsonl"
    if not p.exists():
        raise SystemExit(f"找不到 {p}")
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        for f in CASE_FIELDS:
            if f not in r:
                raise SystemExit(f"runs.jsonl 缺少字段 {f}：{r}")
        gid = r["case_id"]
        sel = tuple(r["selected_skills"] or [])
        out.setdefault(gid, []).append((sel, gold.get(gid, sel)))
    for v in out.values():
        v.sort(key=lambda x: x[0])
    return out


def ctype(cid: str) -> str:
    for t in ("pos", "amb", "rej", "multi", "neg", "tool"):
        if cid.startswith(f"pax-{t}-"):
            return t
    if "-" in cid:
        return cid.split("-")[1]
    return "?"


def per_case_table(a: dict, b: dict, label_a: str, label_b: str) -> list[tuple]:
    cids = sorted(set(a) | set(b), key=lambda x: (ctype(x), x))
    print(f"{'case_id':<16}{'type':<7}{label_a:<14}{label_b:<14}{label_b + ' 预测'}")
    print("-" * 74)
    rows = []
    for cid in cids:
        ra, rb = a.get(cid, []), b.get(cid, [])
        ta = sum(1 for s, g in ra if s == g)
        tb = sum(1 for s, g in rb if s == g)
        na, nb = len(ra), len(rb)
        pred = " / ".join("+".join(s) if s else "(空)" for s, _ in rb[:3])
        print(f"{cid:<16}{ctype(cid):<7}"
              f"{(f'{ta}/{na}' if na else 'n/a'):<14}"
              f"{(f'{tb}/{nb}' if nb else 'n/a'):<14}{pred}")
        rows.append((cid, ta, tb, na, nb))
    return rows


def _line(pa: float, pb: float) -> str:
    """两个百分比相减，返回带符号的 pp 差值。"""
    return f"Δ {pa - pb:+.1f}pp"


def summary(rows: list[tuple], label_a: str, label_b: str) -> None:
    ta, tb = sum(r[1] for r in rows), sum(r[2] for r in rows)
    na = sum(r[3] for r in rows)
    print()
    print(f"合计 exact_set_match：{label_a} {ta}/{na} ({100*ta/na:.1f}%)   "
          f"{label_b} {tb}/{na} ({100*tb/na:.1f}%)")
    print(f"{label_a} 相对 {label_b} 的增益：{100*(ta-tb)/na:+.1f}pp")

    print()
    print("按类型：")
    for ty in sorted({ctype(r[0]) for r in rows}):
        sub = [r for r in rows if ctype(r[0]) == ty]
        a, b, n = sum(r[1] for r in sub), sum(r[2] for r in sub), sum(r[3] for r in sub)
        print(f"  {ty:<6} {label_a} {a:>2}/{n:<2} ({100*a/n:5.1f}%)   "
              f"{label_b} {b:>2}/{n:<2} ({100*b/n:5.1f}%)   {_line(100*a/n, 100*b/n)}")


def extras(run_dir: str, label: str) -> None:
    p = Path(run_dir) / "scores.json"
    if not p.exists():
        return
    s = json.loads(p.read_text(encoding="utf-8"))
    rel = s.get("reliability") or {}
    flaky = s.get("flaky_cases") or []
    print(f"\n{label}（{Path(run_dir).name}）")
    print(f"  stability.exact_set_match = "
          f"{s.get('stability', {}).get('exact_set_match', {}).get('mean')} "
          f"(±{s.get('stability', {}).get('exact_set_match', {}).get('stddev')})")
    print(f"  pass@{rel.get('k')}={rel.get('pass_at_k')}  "
          f"{rel.get('pass_all_label')}={rel.get('pass_all_k')}  "
          f"flaky case {len(flaky)} 个")
    print(f"  by_type = {json.dumps({k: round(v['accuracy'], 3) for k, v in (s.get('by_type') or {}).items()})}")
    eff = (s.get("efficiency") or {}).get("tokens") or {}
    if eff:
        print(f"  tokens/turn = {eff.get('mean')} ± {eff.get('stddev')}")
    if not (s.get("gate_pass")):
        fails = [g["metric"] for g in (s.get("gate") or []) if not g["pass"]]
        print(f"  GATE FAIL：{', '.join(fails)}")
    else:
        print("  GATE PASS")


def failure_modes(runs: dict, gold: dict, label: str) -> None:
    """把误判拆成四种互斥的失败模式。

    exact_set_match 一个数字看不出错在哪，而这四种的修复方向完全不同：
      over_selection   选对了入口但多叠了子 skill  →  改提示/补禁令，不是选错
      dropped_entry    应该选入口却返回空        →  入口描述不够有吸引力
      missing_entry    选了别的 skill           →  语义判别能力问题
      false_activation gold 为空却选了          →  拒答能力问题（与安全性相关）
    """
    bucket: dict[str, list[str]] = {
        "over_selection": [], "dropped_entry": [],
        "missing_entry": [], "false_activation": [],
    }
    denom: dict[str, int] = {"pos": 0, "rej": 0}
    for cid, gold_skills in gold.items():
        for sel, _ in runs.get(cid, []):
            if ctype(cid) == "pos":
                denom["pos"] += 1
            elif ctype(cid) == "rej":
                denom["rej"] += 1
            if set(sel) == set(gold_skills):
                continue
            gs, ss = set(gold_skills), set(sel)
            if not gs:                                   # 拒答题
                bucket["false_activation"].append(cid if sel else cid)
            elif not ss:
                bucket["dropped_entry"].append(cid)
            elif gs <= ss:
                bucket["over_selection"].append(cid)
            else:
                bucket["missing_entry"].append(cid)

    print(f"\n{label} 失败模式拆解：")
    for k in ("over_selection", "dropped_entry", "missing_entry", "false_activation"):
        ids = bucket[k]
        detail = f"  ({', '.join(sorted(set(ids)))})" if len(set(ids)) <= 4 else \
                 f"  ({len(set(ids))} 个 case)"
        print(f"  {k:<18} {len(ids):>3} 次{detail}")
    if denom["pos"]:
        os_n = sum(1 for cid in bucket["over_selection"])
        print(f"  过度选择率（分母 = 正面题判定数 {denom['pos']}）：{100*os_n/denom['pos']:.1f}%")
    if denom["rej"]:
        fa = len(bucket["false_activation"])
        print(f"  误激活率（分母 = 拒答题判定数 {denom['rej']}）：{100*fa/denom['rej']:.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    ap.add_argument("--dataset", help="带 gold 的 jsonl（含 # 注释头）")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    args = ap.parse_args()

    gold = load_dataset(args.dataset)
    a, b = load_runs(args.run_a, gold), load_runs(args.run_b, gold)
    print(f"{args.label_a}: {len(a)} cases × {len(next(iter(a.values())))} repeats")
    print(f"{args.label_b}: {len(b)} cases × {len(next(iter(b.values())))} repeats")
    print(f"case 集合一致: {set(a) == set(b)}")
    if gold:
        print(f"gold 来源: {args.dataset}（{len(gold)} 条）\n")
    else:
        print("⚠️  未提供 --dataset：无法比命中率，只显示稳定性\n")

    if gold:
        rows = per_case_table(a, b, args.label_a, args.label_b)
        summary(rows, args.label_a, args.label_b)

        # B 侧误选分布
        cnt = Counter()
        for cid, runs in b.items():
            for sel, g in runs:
                if sel != g:
                    cnt["+".join(sel) if sel else "(空)"] += 1
        if cnt:
            print(f"\n{args.label_b} 误选分布（非 gold 的预测）：")
            for k, v in cnt.most_common():
                print(f"  {v:>3} 次  →  {k}")

        failure_modes(a, gold, args.label_a)
        print()
        failure_modes(b, gold, args.label_b)
    else:
        per_case_table({}, b, args.label_a, args.label_b)

    print()
    extras(args.run_a, args.label_a)
    print()
    extras(args.run_b, args.label_b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
