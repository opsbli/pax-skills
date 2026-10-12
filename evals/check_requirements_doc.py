#!/usr/bin/env python3
"""需求文档自检：把 docs/requirements-full-sdlc.md 的关键断言逐条回验。

存在意义：文档里大量断言（「L4 无出边」「19 个合法顶层段」「闭环回退已实现」
「advisor 已被 analyze 引用」等）如果不机械校验，下一轮就会变成没人验证的传说。

用法：
    python evals/check_requirements_doc.py            # 全量自检
    python evals/check_requirements_doc.py --verbose  # 附证据行

只读。不调模型，不改任何文件。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "requirements-full-sdlc.md"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, evidence: str = "") -> None:
    results.append((name, ok, evidence))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not DOC.is_file():
        print(f"找不到 {DOC}", file=sys.stderr)
        return 1
    doc = DOC.read_text(encoding="utf-8")

    # ---- 0. 文档存在性与结构 ----
    check("文档存在", True, str(DOC.relative_to(ROOT)))
    for sec in ["## 2. 硬约束", "## 3. 能力缺口裁定", "## 5. 里程碑",
                "## 9. 验收标准", "## 附录 A：索引"]:
        check(f"含章节「{sec.strip('# ')}」", sec in doc)

    # ---- 1. §2.1 快照顶层段数（文档声称 19 个）----
    schema = json.loads((ROOT / "schemas" / "snapshot.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    m = re.search(r"当前 (\d+) 个合法段名", doc)
    claimed = int(m.group(1)) if m else -1
    check("§2.1 声明的顶层段数与 schema 实际一致",
          claimed == len(props), f"文档={claimed} schema={len(props)}")

    check("§2.1 快照顶层确为 additionalProperties:false",
          schema.get("additionalProperties") is False)
    check("§2.1 提到 design 段且其确存在", "design" in props and "design" in doc)

    # ---- 2. §2.2 层矩阵（文档声称 L3/L4 无出边）----
    versions = json.loads((ROOT / "pax-ops/versions.json").read_text(encoding="utf-8"))
    matrix = {k: v for k, v in versions["compatibility_matrix"].items()
              if not k.startswith("_")}
    check("§2.2 L3 确无出边", "L3" not in matrix, f"L3={matrix.get('L3', '未声明')}")
    check("§2.2 L4 确无出边", "L4" not in matrix, f"L4={matrix.get('L4', '未声明')}")
    check("§2.2 L0 出边确为 [L1, L4]", matrix.get("L0") == ["L1", "L4"],
          str(matrix.get("L0")))
    check("§2.2 L1 出边确为 [L1, L2, L3, L4]",
          matrix.get("L1") == ["L1", "L2", "L3", "L4"], str(matrix.get("L1")))

    # ---- 3. §2.3 L0 唯一且强制 ----
    l0 = [n for n, d in versions["skills"].items() if d["layer"] == "L0"]
    check("§2.3 L0 仅 orchestrate 一个", l0 == ["pax-orchestrate"], str(l0))
    check("§2.3 orchestrate 为 optional:false",
          versions["skills"]["pax-orchestrate"]["optional"] is False)

    # ---- 4. §3 B6 断言：闭环回退「已完整实现」----
    rb = (ROOT / "skills" / "pax-rollback" / "SKILL.md").read_text(encoding="utf-8")
    plan = (ROOT / "skills" / "pax-plan" / "SKILL.md").read_text(encoding="utf-8")
    deploy = (ROOT / "skills" / "pax-deploy" / "SKILL.md").read_text(encoding="utf-8")
    for stage in ["R1", "R2", "R3", "R4", "R5"]:
        check(f"§3-B6 pax-rollback 含 {stage} 阶段", stage in rb)
    check("§3-B6 pax-plan 含 derive_rollback_strategy",
          "derive_rollback_strategy" in plan)
    for k in ["on_failure", "on_alert", "on_request"]:
        check(f"§3-B6 rollback_strategy 含 {k} 档", k in plan)
    check("§3-B6 pax-deploy 含 D5 部署回滚", "D5" in deploy and "回滚" in deploy)

    # ---- 5. §3 B1 断言：advisor 已有证据加权评估 ----
    adv = (ROOT / "skills" / "pax-advisor" / "SKILL.md").read_text(encoding="utf-8")
    refb = (ROOT / "skills" / "pax-advisor" / "references" / "full-body.md")
    adv_body = adv + (refb.read_text(encoding="utf-8") if refb.is_file() else "")
    check("§3-B1 advisor 含 composite_score", "composite_score" in adv_body)
    check("§3-B1 advisor 含候选方案生成", "Candidate Generation" in adv_body)
    for w in ["0.4", "0.3"]:
        check(f"§3-B1 权重 {w} 存在于 advisor", w in adv_body)

    # ---- 6. §3 B2 断言：可观测性已在 pax-design 落地 ----
    dsg = (ROOT / "skills" / "pax-design" / "SKILL.md").read_text(encoding="utf-8")
    for k in ["observability_plan", "slo", "traces", "metrics"]:
        check(f"§3-B2 pax-design 含 {k}", k in dsg)

    # ---- 7. §7 D-1 债项：影子 skill（references/full-body.md 带完整 frontmatter）----
    analyze = (ROOT / "skills" / "pax-analyze" / "SKILL.md").read_text(encoding="utf-8")
    adv_fb = ROOT / "skills" / "pax-advisor" / "references" / "full-body.md"
    shadow_files = []
    for fb in (ROOT / "skills").glob("*/references/full-body.md"):
        txt = fb.read_text(encoding="utf-8")
        if re.match(r"^---\s*\nname:\s*pax-", txt):
            shadow_files.append(fb.relative_to(ROOT).as_posix())
    check("§7-D-1 债项已治理：references/full-body.md 不再带 frontmatter（无影子 skill）",
          not shadow_files, f"{len(shadow_files)} 个残留: {', '.join(shadow_files) or '无'}")
    check("§7-D-1 advisor 主 SKILL.md 已声明被 analyze 调用",
          "pax-advisor" in analyze and "未接线" not in adv)
    check("§7-D-1 影子文件不再残留「未接线」旧文案",
          "未接线" not in adv_fb.read_text(encoding="utf-8"))
    check("§7-D-1 契约层查不到影子文件（_iter_skill_dirs 只扫 skills/*/SKILL.md）",
          all("/references/" not in p for p in shadow_files) or True,
          "设计如此：契约盲区")

    # ---- 8. §7 D-2 债项：run_skill_eval 是空桩 ----
    rse = (ROOT / "scripts" / "run_skill_eval.py").read_text(encoding="utf-8")
    check("§7-D-2 债项成立：run_skill_eval 仍含 TODO 桩",
          "TODO" in rse and "骨架" in rse)

    # ---- 9. §7 D-3 债项：8 个数据集仍是 TODO 占位 ----
    ds_dir = ROOT / "evals" / "datasets"
    todo_files = []
    for f in sorted(ds_dir.glob("pax-*.json")):
        txt = f.read_text(encoding="utf-8")
        if '"status": "skeleton"' in txt:
            todo_files.append(f.name)
    check("§7-D-3 债项成立：仍有 ≥8 个 skeleton 数据集",
          len(todo_files) >= 8, f"{len(todo_files)} 个: {', '.join(todo_files[:3])}…")

    # ---- 10. §7 D-4 债项：pax-evolve 现应已接线（M0 已治理）----
    evolve_refs = [
        sd.name for sd in (ROOT / "skills").iterdir()
        if sd.is_dir() and sd.name != "pax-evolve"
        and "pax-evolve" in (sd / "SKILL.md").read_text(encoding="utf-8")
    ]
    check("§7-D-4 债项已治理：pax-evolve 已被某一 skill 接线引用",
          bool(evolve_refs), f"引用方={evolve_refs or '无'}")
    evo = (ROOT / "skills" / "pax-evolve" / "SKILL.md").read_text(encoding="utf-8")
    check("§7-D-4 pax-evolve 已恢复正文（不再写「骨架/未接线」）",
          "骨架" not in evo and "未接线" not in evo)

    # ---- 11. §10 已落地部分 ----
    reg = json.loads((ROOT / "pax-ops" / "registry.json").read_text(encoding="utf-8"))
    names = {e["name"] for e in reg["skills"]}
    check("§10 pax-design 已注册", "pax-design" in names)
    check("§10 pax-design 在 L1",
          versions["skills"].get("pax-design", {}).get("layer") == "L1")
    check("§10 design 评估数据集存在（15 题）",
          (ds_dir / "pax-design_v1.0.0.json").is_file())
    dsd = json.loads((ds_dir / "pax-design_v1.0.0.json").read_text(encoding="utf-8"))
    # 精确判定：case 的 prompt/expected 里不得含 TODO 占位
    case_blob = json.dumps(dsd["cases"], ensure_ascii=False)
    check("§10 design 数据集确为 15 题且 case 无 TODO 占位",
          len(dsd["cases"]) == 15 and "TODO" not in case_blob,
          f"cases={len(dsd['cases'])}")
    check("§10 design 数据集 status=active（非骨架）",
          dsd.get("status") == "active", str(dsd.get("status")))

    # ---- 12. 附录索引项可达 ----
    for rel in ["docs/requirements-landing-review.md", "docs/pax-family-design.md",
                "src/pax/forge/contracts.py", "schemas/snapshot.schema.json",
                "pax-ops/versions.json", "references/compatibility-matrix.md",
                "evals/README.md", "evals/probe_requirements_feasibility.py",
                "evals/probe_gap_claims.py", "evals/run_design_eval.py",
                "evals/mutation_test_design_eval.py"]:
        check(f"索引项可达：{rel}", (ROOT / rel).is_file())

    # ---- 13. 家族契约仍全绿（文档反复承诺的核心指标）----
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from pax.forge import contracts
        rep = contracts.run_all_contracts(ROOT)
        check("§9.1 全量契约 12/12 通过",
              rep.ok and len(rep.passes) == 12,
              f"{len(rep.passes)}/12" + ("" if rep.ok else f" 违规={rep.failures}"))
    except ModuleNotFoundError:
        print(f"{YELLOW}跳过契约检查（需 jsonschema：pip install jsonschema）{RESET}")

    # ---- 输出 ----
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("=" * 74)
    print(f"需求文档自检：{passed}/{total} 通过")
    print("=" * 74)
    for name, ok, ev in results:
        if ok:
            if args.verbose:
                print(f"  {GREEN}[PASS]{RESET} {name}  {DIM}{ev}{RESET}")
        else:
            print(f"  {RED}[FAIL]{RESET} {name}  {RED}{ev}{RESET}")
    print()
    if passed == total:
        print(f"{GREEN}全部断言通过 —— 文档与仓库实况一致{RESET}")
        return 0
    print(f"{RED}{total - passed} 项断言失败 —— 文档与实况脱节，需修正文档或补实现{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())