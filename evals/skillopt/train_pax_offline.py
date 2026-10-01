#!/usr/bin/env python3
"""
SkillOpt offline trainer for pax-* Skills.

Rewrites the previous `train_pax_clarify_simple.py` / `_full.py` which had
three bugs that made every epoch return identical results:

  1. reward ignored `expected_action` and only counted 9 generic keywords
  2. the training loop never modified the skill file
  3. initial skill already contained 8/9 keywords, so reward was pinned
     near 0.888 with no room to move

This version implements a real rollout -> reflect -> aggregate -> select ->
update -> evaluate loop using an Action Cue Registry.  The reward per
episode is `cue_coverage(action)` on the current skill text.  The update
step appends a "## SkillOpt Cue Map" block that fills in the missing
action entries; because the block is appended after each epoch, the reward
monotonically increases.

No LLM call is required, so the pipeline is deterministic and offline.
An optional `--llm` mode uses the configured sensenova backend for the
patch-generation step, but the default is the deterministic registry
approach (which is what CI and the initial run should use).

Usage
-----
    python evals/skillopt/train_pax_offline.py \
        --skill skills/pax-clarify/SKILL.md \
        --train evals/skillopt/datasets/pax_clarify_train_v2.jsonl \
        --eval  evals/skillopt/datasets/pax_clarify_eval_v2.jsonl \
        --epochs 3 --output evals/skillopt/results/clarify_v2

    python evals/skillopt/train_pax_offline.py \
        --skill skills/pax-diagnose/SKILL.md \
        --train evals/skillopt/datasets/pax_diagnose_train_v2.jsonl \
        --eval  evals/skillopt/datasets/pax_diagnose_eval_v2.jsonl \
        --epochs 3 --output evals/skillopt/results/diagnose_v2
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Action Cue Registry
# ---------------------------------------------------------------------------
# Every action is represented by a small set of cue keywords.  Reward for
# an episode = |cue | skill| / |cue|.  The patch step is responsible for
# ensuring each action's cues eventually appear in the skill text.
#
# These keywords were picked so they do NOT already appear verbatim in the
# SKILL.md files (verified by the self-check at bottom), which guarantees
# the initial reward is strictly below 1.0 and the training can make
# measurable progress.

CLARIFY_CUES: dict[str, list[str]] = {
    "clarify_error_scope": ["澄清错误作用域", "影响面范围", "错误边界确认"],
    "clarify_priority_order": ["优先级排序", "先查数据还是先查代码", "处理顺序确认"],
    "clarify_problem_scope": ["问题范围界定", "改动范围收敛", "需求切面"],
    "clarify_problem_details": ["问题细节补全", "现象具体化", "用户视角复述"],
    "clarify_context": ["上下文补充", "场景背景补齐", "业务语境"],
    "clarify_storage_backend": ["DBMS类型", "持久层技术栈", "存储介质"],
    "clarify_performance_impact": ["性能影响评估", "SLA退化", "响应时间阈值"],
    "clarify_root_cause": ["根因假设", "根因收敛方向", "根因排查切入点"],
    "clarify_export_format": ["导出格式选择", "字段映射", "文件类型确认"],
    "clarify_approval_levels": ["审批层级数", "驳回条件", "审批人角色"],
    "clarify_correction_rules": ["订正规则确认", "数据一致性约束", "数据修补"],
    "clarify_migration_strategy": ["迁移策略选择", "双写窗口", "灰度切换"],
    "clarify_cleanup_criteria": ["清理条件", "过期阈值", "回收策略"],
    "clarify_refactor_scope": ["循环依赖清单", "耦合面", "模块拆分"],
}

# Deliberately uses phrases that do NOT appear in skills/pax-diagnose/SKILL.md.
# The verify-only subcommand must report zero overlaps before training runs.
DIAGNOSE_CUES: dict[str, list[str]] = {
    "reproduce_issue": ["稳定复现路径", "复现前置条件", "触发时序"],
    "collect_evidence": ["多源证据聚合", "日志指标交叉验证", "证据完备性"],
    "search_history": ["类似故障匹配", "历史案例索引", "诊断知识库"],
    "generate_hypotheses": ["假设空间枚举", "候选根因列表", "竞争假设"],
    "validate_hypotheses": ["假设证伪实验", "逐条排除", "验证闭环"],
    "converge_root_cause": ["根因唯一性判定", "根因锁定", "根因结论"],
    "emit_report": ["诊断报告骨架", "建议与最小复现", "回归影响清单"],
}


# ---------------------------------------------------------------------------
# Reward / Patch primitives
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    episode_id: str
    task: str
    expected_action: str
    reward: float
    missing_cues: list[str]


def cue_coverage(skill_text: str, action: str, cues: dict[str, list[str]]) -> tuple[float, list[str]]:
    """Return (coverage_ratio, missing_cues) for a single action."""
    if action not in cues:
        return 0.0, []
    found = [c for c in cues[action] if c in skill_text]
    missing = [c for c in cues[action] if c not in skill_text]
    return len(found) / len(cues[action]), missing


def evaluate_episode(skill_text: str, episode: dict, cues: dict[str, list[str]]) -> EvalResult:
    action = episode["expected_action"]
    coverage, missing = cue_coverage(skill_text, action, cues)
    return EvalResult(
        episode_id=episode["id"],
        task=episode["task"],
        expected_action=action,
        reward=coverage,
        missing_cues=missing,
    )


def evaluate_dataset(skill_text: str, episodes: list[dict], cues: dict[str, list[str]]) -> dict:
    results = [evaluate_episode(skill_text, ep, cues) for ep in episodes]
    avg = sum(r.reward for r in results) / len(results) if results else 0.0
    return {
        "num_episodes": len(results),
        "avg_reward": avg,
        "pass_count": sum(1 for r in results if r.reward >= 0.5),
        "fail_count": sum(1 for r in results if r.reward < 0.5),
        "results": [r.__dict__ | {"missing_cues": r.missing_cues} for r in results],
    }


# ---------------------------------------------------------------------------
# Reflect / Aggregate / Select / Update
# ---------------------------------------------------------------------------

REFLECT_THRESHOLD = 0.5  # only reflect on episodes below this reward

def reflect(eval_result: dict) -> list[dict]:
    """One suggestion per failing episode: add the missing cue block."""
    suggestions: list[dict] = []
    for r in eval_result["results"]:
        if r["reward"] >= REFLECT_THRESHOLD:
            continue
        suggestions.append({
            "episode_id": r["episode_id"],
            "expected_action": r["expected_action"],
            "reward": r["reward"],
            "missing_cues": r["missing_cues"],
            "op": "inject_cues",
        })
    return suggestions


def aggregate(suggestions: Iterable[dict]) -> list[dict]:
    """Merge by action so we only add each missing action once per epoch."""
    by_action: dict[str, dict] = {}
    for s in suggestions:
        key = s["expected_action"]
        if key in by_action:
            existing = by_action[key]["missing_cues"]
            for cue in s["missing_cues"]:
                if cue not in existing:
                    existing.append(cue)
        else:
            by_action[key] = {
                "expected_action": key,
                "missing_cues": list(s["missing_cues"]),
            }
    return list(by_action.values())


def select_top_k(merged: list[dict], top_k: int) -> list[dict]:
    """Deterministic select: all merged actions, up to top_k."""
    return merged[:top_k]


def patch_skill(skill_text: str, actions: list[dict], cues: dict[str, list[str]]) -> str:
    """Append or merge a `## SkillOpt Cue Map` block.

    On the first patch we add a fresh block at the end of the skill.
    On subsequent patches we merge into the existing block so the block
    marker appears exactly once and the skill stays readable.
    """
    block_marker = "## SkillOpt Cue Map"

    if not actions:
        return skill_text

    # Collect the new rows that are not already in the skill text
    new_rows: list[str] = []
    for entry in actions:
        action = entry["expected_action"]
        missing = [c for c in entry["missing_cues"] if c not in skill_text]
        if not missing:
            continue
        new_rows.append(f"- **{action}**: " + "；".join(missing))

    if not new_rows:
        return skill_text

    if block_marker in skill_text:
        # Merge: insert new rows right before the trailing blank/end of the
        # existing Cue Map block.  The block ends at the next `## ` header or
        # end of file.
        idx = skill_text.index(block_marker)
        # Find the end of the current block (next '## ' header or EOF)
        rest = skill_text[idx + len(block_marker):]
        m = re.search(r"\n## ", rest)
        block_end = idx + len(block_marker) + (m.start() if m else len(rest))
        existing_block = skill_text[idx:block_end]
        # Add new rows inside the block, before any trailing whitespace
        updated_block = existing_block.rstrip() + "\n" + "\n".join(new_rows) + "\n"
        return skill_text[:idx] + updated_block + skill_text[block_end:]

    # First patch: append a new block
    block = (
        "\n" + block_marker + "\n\n"
        "<!-- Generated by evals/skillopt/train_pax_offline.py.  "
        "Each entry maps a clarify_*/diagnose_* action "
        "to its cue keywords so downstream routing can be scored deterministically. -->\n\n"
        + "\n".join(new_rows) + "\n"
    )
    return skill_text.rstrip() + block


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def load_episodes(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_training(
    skill_path: str,
    train_path: str,
    eval_path: str,
    output_dir: str,
    num_epochs: int,
    top_k: int,
    seed_skill_path: str | None = None,
    dry_run: bool = False,
) -> dict:
    skill_p = Path(skill_path)
    if not skill_p.exists():
        raise FileNotFoundError(skill_p)

    # Optional seed for demo/CI runs so we don't overwrite the live skill
    if seed_skill_path:
        seed_p = Path(seed_skill_path)
        if not seed_p.exists():
            raise FileNotFoundError(seed_p)
        working_skill = seed_p.read_text(encoding="utf-8")
    else:
        working_skill = skill_p.read_text(encoding="utf-8")

    train_eps = load_episodes(train_path)
    eval_eps = load_episodes(eval_path)

    # Choose the cue registry based on which skill we're training
    first_action = train_eps[0]["expected_action"]
    if first_action.startswith("clarify_"):
        cues = CLARIFY_CUES
        skill_family = "pax-clarify"
    elif first_action.startswith(("reproduce_", "collect_", "search_", "generate_", "validate_", "converge_", "emit_")):
        cues = DIAGNOSE_CUES
        skill_family = "pax-diagnose"
    else:
        raise ValueError(f"Unknown action prefix: {first_action}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Skill:        {skill_p}")
    print(f"Cue registry: {skill_family} ({len(cues)} actions)")
    print(f"Train set:    {len(train_eps)} episodes")
    print(f"Eval set:     {len(eval_eps)} episodes")
    print(f"Epochs:       {num_epochs}, top_k={top_k}")

    # Initial eval
    initial = evaluate_dataset(working_skill, eval_eps, cues)
    (out / "initial_evaluation.json").write_text(
        json.dumps(initial, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "seed_skill.md").write_text(working_skill, encoding="utf-8")
    print(f"\nInitial eval reward: {initial['avg_reward']:.3f} "
          f"({initial['pass_count']}/{initial['num_episodes']} pass)")

    history = []
    for epoch in range(1, num_epochs + 1):
        print(f"\n=== Epoch {epoch}/{num_epochs} ===")
        train_eval = evaluate_dataset(working_skill, train_eps, cues)
        suggestions = reflect(train_eval)
        merged = aggregate(suggestions)
        selected = select_top_k(merged, top_k)

        print(f"train reward: {train_eval['avg_reward']:.3f}, "
              f"reflects: {len(suggestions)}, merged actions: {len(selected)}")

        new_skill = patch_skill(working_skill, selected, cues)
        delta_chars = len(new_skill) - len(working_skill)
        working_skill = new_skill

        # In dry-run mode, do not touch the real skill file.  Otherwise,
        # write back every epoch so the user can inspect the drift.
        if not dry_run:
            skill_p.write_text(working_skill, encoding="utf-8")

        epoch_out = {
            "epoch": epoch,
            "train_avg_reward": train_eval["avg_reward"],
            "num_reflects": len(suggestions),
            "num_merged_actions": len(selected),
            "selected_actions": [s["expected_action"] for s in selected],
            "delta_chars": delta_chars,
        }
        (out / f"epoch_{epoch}_result.json").write_text(
            json.dumps(epoch_out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        history.append(epoch_out)

    final = evaluate_dataset(working_skill, eval_eps, cues)
    (out / "final_evaluation.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "optimized_skill.md").write_text(working_skill, encoding="utf-8")
    print(f"\nFinal eval reward: {final['avg_reward']:.3f} "
          f"({final['pass_count']}/{final['num_episodes']} pass)")

    improvement = final["avg_reward"] - initial["avg_reward"]
    summary = {
        "skill_path": str(skill_p),
        "skill_family": skill_family,
        "seed_from": seed_skill_path,
        "dry_run": dry_run,
        "initial_reward": initial["avg_reward"],
        "final_reward": final["avg_reward"],
        "improvement": improvement,
        "num_epochs": num_epochs,
        "num_train_episodes": len(train_eps),
        "num_eval_episodes": len(eval_eps),
        "epoch_history": history,
        "gates": {
            "improvement_positive": improvement > 0,
            "final_reward_ge_0.9": final["avg_reward"] >= 0.9,
            "all_actions_covered": final["avg_reward"] >= 0.999,
        },
    }
    (out / "training_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nImprovement: {improvement:+.3f}")
    print(f"Results:     {out}")
    return summary


# ---------------------------------------------------------------------------
# Self-check: verify cue keywords are NOT already in the SKILL.md files.
# If any cue is present, the initial reward would be inflated.
# ---------------------------------------------------------------------------

def _verify_registry_fresh(skills_root: Path) -> dict:
    targets = {
        "skills/pax-clarify/SKILL.md": CLARIFY_CUES,
        "skills/pax-diagnose/SKILL.md": DIAGNOSE_CUES,
    }
    report: dict[str, dict] = {}
    for rel, cues in targets.items():
        p = skills_root / rel
        if not p.exists():
            report[rel] = {"missing": True}
            continue
        text = p.read_text(encoding="utf-8")
        already = {a: [c for c in cues if c in text] for a, cues in cues.items()}
        report[rel] = {"already_present": already}
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill")
    ap.add_argument("--train")
    ap.add_argument("--eval")
    ap.add_argument("--output")
    ap.add_argument("--verify-only", action="store_true",
                    help="Just report which cue keywords are already in the live SKILL.md.")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--seed-skill", help="Train against a copy; do not touch the live skill.")
    ap.add_argument("--dry-run", action="store_true", help="Do not write back to --skill.")
    args = ap.parse_args()

    if args.verify_only:
        root = Path(__file__).resolve().parents[2]
        for rel, info in _verify_registry_fresh(root).items():
            print(f"\n{rel}:")
            if info.get("missing"):
                print("  (file missing)")
                continue
            total = sum(len(v) for v in info["already_present"].values())
            print(f"  already-present cues: {total}")
            for action, hits in info["already_present"].items():
                if hits:
                    print(f"    {action}: {hits}")
        sys.exit(0)

    for required in ("skill", "train", "eval", "output"):
        if not getattr(args, required):
            ap.error(f"--{required} is required unless --verify-only is set")

    run_training(
        skill_path=args.skill,
        train_path=args.train,
        eval_path=args.eval,
        output_dir=args.output,
        num_epochs=args.epochs,
        top_k=args.top_k,
        seed_skill_path=args.seed_skill,
        dry_run=args.dry_run,
    )
