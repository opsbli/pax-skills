#!/usr/bin/env python3
"""生成 description 对照组：剥离「不要直接选择」类禁令的 skill 集与套件。

为什么需要这个对照组
--------------------
pax_routing v2.0 的外部路由评估跑出 100% 命中率，但 18 个 description 里有 13 条写着
「不要直接选择」、1 条写着「应选择 pax-orchestrate」。catalog 有 18 个条目，按描述自身
的规则却只有 1 个是候选的——所以那个 100% 测的是「模型遵守 17 条显式禁令」，不是
「模型在 17 个语义竞争的 skill 里做判断」。

本脚本剥掉禁令、保留能力描述，跑一遍同条件下的评估，才能量出禁令贡献了多少命中率。

剥离规则（只改 frontmatter description，正文一字不动）
-----------------------------------------------------
1. 「此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。」  → 整句删除
2. 「此 skill 由 pax-orchestrate 在编排路由中调用，当用户报告异常…应选择 pax-orchestrate。」 → 整句删除
3. 「…调用，用于<能力说明>。」 → 保留能力说明，只删前半句
4. 「不要直接选择 pax-diagnose、pax-plan、pax-execute 等具体 skill，而是让
   pax-orchestrate 决定完整的执行路由。」（pax-orchestrate 自身） → 整句删除
5. 「当用户报告异常、报错或性能下降时，应选择 pax-orchestrate。」（pax-diagnose 尾句） → 整句删除

刻意保留的东西
--------------
- pax-orchestrate 自述「统一入口」「必须先经过 pax-orchestrate」——那是它自己的身份，
  不是对别的 skill 的禁令。对照组只回答一个问题：不给禁令，模型还选不选它？
- 各 skill 的「Use when: <能力描述>」正文与全部 frontmatter 其他字段。

用法
----
    python evals/build_control_subjects.py          # 生成对照组 + 对照组套件
    python evals/build_control_subjects.py --check  # 只校验对照组是否漂移，不写文件
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "evals" / "subjects"
DST = ROOT / "evals" / "subjects_control_no_prohibition"
SUITES = ROOT / "evals" / "suites"
SRC_SUITE = SUITES / "pax_routing.yaml"
DST_SUITE = SUITES / "pax_routing_control.yaml"

# 顺序敏感：更具体的模式放前面。全部只作用于 frontmatter 的 description 字段。
RULES: list[tuple[re.Pattern[str], str]] = [
    # 变体：禁令 + 反向指路（仅 pax-diagnose）
    (re.compile("此 skill 由 pax-orchestrate 在编排路由中调用，"
                "当用户报告异常、报错或性能下降时，应选择 pax-orchestrate。"), ""),
    # 变体：纯禁令，能力说明已在前句
    (re.compile("此 skill 由 pax-orchestrate 在编排路由中调用，不要直接选择。"), ""),
    # 变体：禁令 + 「用于<能力说明>」尾句——保留能力说明
    (re.compile("此 skill 由 pax-orchestrate 在编排路由中调用，用于"), "用于"),
    # pax-orchestrate 自身的「不要直接选择具体 skill」禁令
    (re.compile("不要直接选择 pax-diagnose、pax-plan、pax-execute 等具体 skill，"
                "而是让 pax-orchestrate 决定完整的执行路由。"), ""),
    # 反向指路：同样是指令，不是能力描述（pax-diagnose）
    (re.compile("当用户报告异常、报错或性能下降时，应选择 pax-orchestrate。"), ""),
]

# description 块：`description: >` 之后缩进 4 空格的续行。frontmatter 内唯一匹配。
DESC_RE = re.compile(r"(description:\s*>\s*\n)((?:    .+\n)+)", re.M)
FRONTMATTER_END = "\n---"


def _strip_desc(text: str) -> tuple[str, list[str]]:
    """剥离 description 中的禁令。返回 (新文本, 命中的规则描述列表)。"""
    m = DESC_RE.search(text)
    if not m:
        return text, []
    block, hits = m.group(2), []
    for pat, repl in RULES:
        if pat.search(block):
            hits.append(pat.pattern[:40])
            block = pat.sub(repl, block)
    # 清理剥离后残留的多余标点（句首孤立句号、连续句号）
    block = re.sub(r"\n\s*。\s*", "\n", block)
    return text[: m.start(2)] + block + text[m.end(2):], hits


def _all_descs(text: str) -> list[str]:
    out = []
    for m in DESC_RE.finditer(text):
        out.append(" ".join(l.strip() for l in m.group(2).strip().split("\n")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="只校验对照组是否漂移，不写文件")
    args = ap.parse_args()

    src_files = sorted(SRC.glob("*/v1/SKILL.md"))
    if not src_files:
        print(f"错误：{SRC} 下没有 SKILL.md", file=sys.stderr)
        return 1

    changed, kept = [], []
    for src in src_files:
        text = src.read_text(encoding="utf-8")
        new_text, hits = _strip_desc(text)
        rel = src.relative_to(SRC)
        dst = DST / rel
        rec = {"skill": rel.parts[0], "dst": dst, "src": src,
               "before": _all_descs(text)[0], "after": _all_descs(new_text)[0],
               "hits": hits}
        if new_text != text:
            changed.append(rec)
            if not args.check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(new_text, encoding="utf-8")
        else:
            kept.append(rec)

    total = len(changed) + len(kept)
    print(f"扫描 {total} 个 skill：剥离 {len(changed)} 个，未命中 {len(kept)} 个\n")
    for rec in changed:
        print(f"[剥离] {rec['skill']}  ({len(rec['before'])} → {len(rec['after'])} 字)")
        print(f"   前：{rec['before']}")
        print(f"   后：{rec['after']}")
    if kept:
        print("\n未命中（description 本就不含禁令）：",
              ", ".join(r["skill"] for r in kept))

    if args.check:
        # 校验：对照组目录是否与当前 subjects/ 一致
        drift = []
        for rec in changed + kept:
            dst = rec["dst"]
            if not dst.exists():
                drift.append(f"缺失 {rec['skill']}")
            elif dst.read_text(encoding="utf-8") != (_strip_desc(
                    rec["src"].read_text(encoding="utf-8"))[0]):
                drift.append(f"内容漂移 {rec['skill']}")
        if drift:
            print(f"\n⚠️  对照组漂移 {len(drift)} 处：")
            for d in drift:
                print("  -", d)
            print("   修复：python evals/build_control_subjects.py")
            return 1
        print(f"\n✓ 对照组与 skills/ 一致（含 {len(list(DST.glob('*/v1/SKILL.md')))} 个 skill）")
        return 0

    # 生成对照组套件：与 v2.0 唯一差异是 suite_id/suite_version/skills.dir
    suite = SRC_SUITE.read_text(encoding="utf-8")
    suite = suite.replace(
        "# pax_routing — pax-* 家族路由基线评估套件（routing_only）",
        "# pax_routing_control — description 对照组（剥离「不要直接选择」禁令）\n"
        "#\n"
        "# 用途：v2.0 基线的 100% 命中率是在「13 条 description 明写不要直接选择」的条件下\n"
        "# 得到的。本套件把禁令剥掉、保留能力描述，与 v2.0 同模型同参数同数据集，\n"
        "# 用来量出禁令贡献了多少命中率，即模型在无指示下的真实区分能力。\n"
        "# 生成方式：python evals/build_control_subjects.py（skills.dir 指向派生的对照组目录）",
    )
    suite = suite.replace("suite_id: pax_routing\n", "suite_id: pax_routing_control\n", 1)
    # 版本号从基线套件读取实际值再追加 -control 后缀，避免硬编码后升级版本就静默失效
    m = re.search(r'suite_version:\s*"([^"]+)"', suite)
    if m:
        base = m.group(1).replace("-control", "")
        suite = suite.replace(f'suite_version: "{m.group(1)}"\n',
                              f'suite_version: "{base}-control"\n', 1)
        print(f"对照组套件版本：{base} → {base}-control")
    # skills.dir 只替换最后一段目录名，保留基线套件里的路径形式（绝对或相对均可）。
    # 直接硬编码绝对路径会在基线改用相对路径后静默失效。
    m_dir = re.search(r'^  dir: (.+)$', suite, re.M)
    if m_dir:
        base_dir = m_dir.group(1).strip()
        stem, sep, tail = base_dir.rpartition('/') if '/' in base_dir else base_dir.rpartition('\\')
        sep = sep or '/'
        new_dir = f"{stem}{sep}subjects_control_no_prohibition" if stem else "subjects_control_no_prohibition"
        suite = suite.replace(
            "  # 由 evals/sync_subjects.py 从 skills/ 生成；skills/ 是唯一事实源。\n"
            f"  dir: {base_dir}",
            "  # 由 evals/build_control_subjects.py 从 subjects/ 派生；勿手工编辑。\n"
            "  # 与 subjects/ 的唯一差异：frontmatter description 剥离了「不要直接选择」类禁令。\n"
            f"  dir: {new_dir}",
            1,
        )
        print(f"对照组 skills.dir：{base_dir} → {new_dir}")
    DST_SUITE.write_text(suite, encoding="utf-8")
    print(f"\n已生成对照组套件：{DST_SUITE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
