#!/usr/bin/env python3
"""同步 skills/ -> evals/subjects/，生成 skillEval 需要的被测对象布局。

skillEval 要求 `<root>/<skill-id>/<version>/SKILL.md`（contracts/skill.py §7.3b），
而 pax-* 的唯一事实源是 `skills/<skill-id>/SKILL.md`（无版本目录）。
所以 evals/subjects/ 是**派生产物**，本脚本是唯一生成入口，避免手工拷贝导致漂移。

用法：
    python evals/sync_subjects.py            # 同步并报告增删
    python evals/sync_subjects.py --check    # 只校验一致性，不改文件，漂移时退出码 1

注意：skillEval 用 SKILL.md 的 frontmatter `name` 作为 skill_id，不取目录名。
本脚本按目录名建目录，因此两者必须一致——不一致会在这里报错而不是悄悄错位。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
SUBJECTS = ROOT / "evals" / "subjects"
VERSION = "v1"


def frontmatter_name(path: Path) -> str | None:
    """取出 SKILL.md frontmatter 里的 name 值。零依赖：只按 --- 围栏取文本。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def sync(check_only: bool) -> int:
    problems: list[str] = []

    if not SKILLS.is_dir():
        print(f"找不到事实源目录：{SKILLS}", file=sys.stderr)
        return 2

    sources: dict[str, Path] = {}
    for md in sorted(SKILLS.glob("*/SKILL.md")):
        skill_id = md.parent.name
        declared = frontmatter_name(md)
        if not declared:
            problems.append(f"skills/{skill_id}/SKILL.md 没有可解析的 frontmatter name")
            continue
        if declared != skill_id:
            problems.append(
                f"skills/{skill_id}/SKILL.md 的 frontmatter name={declared!r} "
                f"与目录名 {skill_id!r} 不一致；skillEval 用 name 当 skill_id，"
                f"会导致 include/exclude 全部错位"
            )
        sources[skill_id] = md

    # 布局是 <subjects>/<skill-id>/<version>/SKILL.md，所以 skill_id 在 parts[-2] 的两级。
    SUBJECTS.mkdir(parents=True, exist_ok=True)
    current = {p.parent.parent.name for p in SUBJECTS.glob(f"*/{VERSION}/SKILL.md")}

    missing = sorted(set(sources) - current)
    if not check_only:
        for skill_id in missing:
            target = SUBJECTS / skill_id / VERSION
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text(
                sources[skill_id].read_text(encoding="utf-8"), encoding="utf-8"
            )

    # 漂移：事实源改过了但派生副本没跟上。sync 模式下刚写完成本就是零，只在校验时报。
    stale: list[str] = []
    if check_only:
        for skill_id, src in sources.items():
            dst = SUBJECTS / skill_id / VERSION / "SKILL.md"
            if not dst.exists() or dst.read_text(encoding="utf-8") != src.read_text(encoding="utf-8"):
                stale.append(skill_id)

    if stale:
        problems.append(
            "evals/subjects/ 与 skills/ 内容不一致：" + ", ".join(sorted(stale))
            + "\n  → 重跑 `python evals/sync_subjects.py` 修复"
        )

    if check_only:
        print(
            f"checked {len(sources)} skills "
            f"({len(current)} present in evals/subjects/), {len(stale)} drifted"
        )
    else:
        print(f"skills/ 共 {len(sources)} 个；新增到 evals/subjects/：{missing or '无'}")

    if problems:
        for p in problems:
            print("  ERROR: " + p, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验一致性，不改文件")
    args = parser.parse_args()
    sys.exit(sync(args.check))
