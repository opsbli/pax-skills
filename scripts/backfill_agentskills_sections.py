#!/usr/bin/env python3
"""Backfill agentskills-ci recommended sections into every pax-* SKILL.md.

Inserts, right after the `# <skill-name>` title:
  ## Overview
  ## When to Use
  ## Common Pitfalls
  ## Verification Checklist

The validator (tools/agentskills-ci/src/agentskills_ci/validators.py) does a
lowercase substring search, so the English anchors above are matched by the
validator while the surrounding prose stays in Chinese.

Also prepends a 'Use when ...' trigger to the frontmatter `description`
when it does not already start with a trigger keyword, and copies
references/domain-dependencies.md into skills/<name>/references/ for the
two L0/L1 skills that reference it.

Idempotent: re-running does not duplicate sections.

NOTE: the "Common Pitfalls" prose deliberately avoids literal `pax-*`
names because the no-cycles contract treats any body mention as a call
edge.  Cross-layer references are expressed via layer names instead
("L0 编排层", "L1 执行层", "多专家盲审", etc.).
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

SKILLS_DIR = Path("skills")
SHARED_REFERENCES = Path("references")
SECTIONS_MARKER = "## Overview"

SECTIONS_TEMPLATE = """## Overview

{overview}

## When to Use

{when_to_use}

## Common Pitfalls

{common_pitfalls}

## Verification Checklist

- [ ] {chk1}
- [ ] {chk2}
- [ ] {chk3}
"""

SECTIONS_DATA: dict[str, dict[str, str]] = {
    "pax-orchestrate": {
        "overview": "pax-family 统一入口。对每个任务先做意图分类（6 类 MECE 意图）与四维风险评分（不可逆性 / 影响范围 / 不确定性 / 协调成本），再据此构建执行路由并初始化跨 Skill 快照。",
        "when_to_use": "所有 pax-family 任务默认从这里开始：诊断修复、功能开发、重构优化、数据操作、文档咨询、工具构建。用户或上层 Agent 明确点名要编排时直接进入。",
        "common_pitfalls": (
            "- 直接调用 L1 具体 Skill 绕过路由，导致风险分级缺失。\n"
            "- 高风险动作（部署 / 数据订正 / 破坏性命令）未获得用户明确 approval / confirm 就下发。\n"
            "- 未初始化快照，下游 Skill 拿不到跨阶段状态。"
        ),
        "chk1": "已完成意图分类且分类结果与 6 类 MECE 表一一对应",
        "chk2": "已计算四维风险分并标注等级，高风险任务已向用户显式请求 approval / confirm",
        "chk3": "已初始化快照并把路由表写入快照，可以交给 L1 Skill",
    },
    "pax-clarify": {
        "overview": "共识状态机驱动的澄清 Skill。围绕 6 个共识维度 × 5 个状态，通过问题生成与前沿计算收敛模糊需求。",
        "when_to_use": "用户目标模糊、需求不完整、或存在多种可能理解；编排层判定需要澄清时进入。",
        "common_pitfalls": (
            "- 一次问太多问题，用户回答质量下降。\n"
            "- 未记录共识状态机状态，下游无法判断澄清是否收敛。\n"
            "- 跳过存储后端 / 影响面等硬约束维度，直接进入执行。"
        ),
        "chk1": "所有 6 个共识维度状态已更新，收敛维度达到目标精度",
        "chk2": "已生成并记录待澄清问题清单，标注优先级与预期答案",
        "chk3": "输出契约的澄清结果已写入快照，可以交给下游 Skill",
    },
    "pax-diagnose": {
        "overview": "根因诊断 Skill。D1-D6 工作流：复现 → 证据收集 → 假设生成 → 假设验证 → 根因收敛 → 报告。",
        "when_to_use": "任务路由识别为 diagnose_fix 意图，或高风险执行前需要独立根因判断时。",
        "common_pitfalls": (
            "- 直接跳到假设生成，未做 D1 复现和 D2 证据收集。\n"
            "- 假设空间过小，漏掉真正根因。\n"
            "- 未做 D2.5 历史诊断检索，重复造轮子。"
        ),
        "chk1": "已产出稳定复现路径并写入快照",
        "chk2": "已收集多源证据并列出候选根因列表",
        "chk3": "已锁定唯一根因并给出最小复现与建议",
    },
    "pax-plan": {
        "overview": "结构化规划 Skill。基于澄清结果生成执行计划：任务分解、依赖排序、验收标准、回滚预案。",
        "when_to_use": "澄清已收敛，编排层判定需要执行且任务规模超出单步操作时。",
        "common_pitfalls": (
            "- 计划粒度太粗，执行阶段无法追踪。\n"
            "- 数据订正 / 跨仓库变更未标注 prerequisite 与 script_language 守卫。\n"
            "- 未定义验收标准，评审无锚点。"
        ),
        "chk1": "计划中每个任务都有 owner、依赖、验收标准",
        "chk2": "已检查数据订正守卫与跨仓库守卫字段",
        "chk3": "计划已写入快照，可以交给执行层",
    },
    "pax-execute": {
        "overview": "在契约约束下执行规划。每步执行前校验前置条件，执行后校验输出，跨仓库操作强制走 execution_strategy。",
        "when_to_use": "已有明确计划且前置条件满足，编排层路由到执行阶段。",
        "common_pitfalls": (
            "- 未校验跨仓库 / 跨服务守卫就直接下发破坏性命令。\n"
            "- 执行中未更新快照，下游 Skill 拿不到进度。\n"
            "- 失败时未回滚或告警。"
        ),
        "chk1": "每一步执行前都完成了前置条件校验",
        "chk2": "执行结果与契约输出一致，快照已更新",
        "chk3": "失败路径已触发告警或回滚，用户已确认下一步",
    },
    "pax-review": {
        "overview": "独立评审门禁。以契约为准独立评估执行结果，判定通过 / 有条件通过 / 拒绝。",
        "when_to_use": "执行完成后，进入评审阶段；高风险任务强制经过此 Skill。",
        "common_pitfalls": (
            "- 与执行阶段同一 Agent 评审，缺乏独立性。\n"
            "- 只评审结果，未评审过程与审计留痕。\n"
            "- 拒绝时未给出可执行的修复清单。"
        ),
        "chk1": "评审结论有明确的通过 / 有条件通过 / 拒绝",
        "chk2": "评审意见包含可执行修复清单并写入快照",
        "chk3": "评审留痕完整（输入、检查点、结论、时间戳）",
    },
    "pax-advisor": {
        "overview": "单点咨询 Skill。针对一个具体问题给出建议，不改动任何状态。",
        "when_to_use": "用户或上层 Agent 想要一个专家观点，但不希望触发完整执行流程。",
        "common_pitfalls": (
            "- 建议过宽泛，缺乏可执行性。\n"
            "- 越界触发本应交给多专家盲审的决策。\n"
            "- 未留下建议留痕。"
        ),
        "chk1": "建议针对单一问题，边界清晰",
        "chk2": "建议附有依据与不确定性说明",
        "chk3": "建议留痕写入快照，可以追溯",
    },
    "pax-council": {
        "overview": "多专家盲审 Skill。并行召集多个专家 Agent 独立评审，再汇总分歧。",
        "when_to_use": "高风险、跨团队、或多视角必要；编排层判定为需要盲审的决策。",
        "common_pitfalls": (
            "- 专家视角过窄，未覆盖风险、合规、性能等维度。\n"
            "- 未隔离专家视角，导致回声室。\n"
            "- 汇总时未处理分歧，直接采纳多数意见。"
        ),
        "chk1": "已召集至少 3 个专家且视角互补",
        "chk2": "分歧已被显式记录并给出裁决理由",
        "chk3": "汇总结论有可执行结论与反对意见留痕",
    },
    "pax-worker-research": {
        "overview": "研究型子任务 Skill。有界、单点，只做调研产出结论。",
        "when_to_use": "上层需要一项调研结果（例如查一个库、验证一个说法）时。",
        "common_pitfalls": (
            "- 任务边界外扩，越权做决策。\n"
            "- 未记录证据来源。\n"
            "- 未回收到上层快照。"
        ),
        "chk1": "调研范围明确且未越界",
        "chk2": "结论附有证据链",
        "chk3": "结果已回收到上层快照",
    },
    "pax-worker-implement": {
        "overview": "实现型子任务 Skill。有界、单点，只做一个可交付的实现步骤。",
        "when_to_use": "上层计划中有一个独立的实现子任务需要落地。",
        "common_pitfalls": (
            "- 一次做太多子任务，输出失控。\n"
            "- 破坏原有文件结构。\n"
            "- 未回滚失败改动。"
        ),
        "chk1": "子任务边界明确且交付可验证",
        "chk2": "改动文件清单已回收到上层快照",
        "chk3": "失败路径可回滚",
    },
    "pax-verify": {
        "overview": "运行中验证 Skill。在长任务执行过程中周期性检查契约与前置条件。",
        "when_to_use": "长耗时任务执行中，编排层或运行监控触发验证。",
        "common_pitfalls": (
            "- 验证频率过高影响执行效率。\n"
            "- 只检查静态契约，忽略运行时状态。\n"
            "- 发现问题后未告警。"
        ),
        "chk1": "验证频率与任务时长匹配",
        "chk2": "验证覆盖静态契约和运行时状态",
        "chk3": "异常已触发告警并写入快照",
    },
    "pax-evolve": {
        "overview": "自进化 Skill。汇总过往执行留痕，提出 Skill 文档 / 契约的改进建议。",
        "when_to_use": "定期或积累足够执行留痕后，主动或按需运行。",
        "common_pitfalls": (
            "- 建议过于主观，缺乏证据支撑。\n"
            "- 建议破坏现有契约兼容性。\n"
            "- 未走 PR / review 流程直接落盘。"
        ),
        "chk1": "每条改进建议都有支撑证据",
        "chk2": "建议与兼容矩阵一致",
        "chk3": "改动以 PR / patch 形式提交，不直接改生产文件",
    },
    "pax-docs": {
        "overview": "文档沉淀 Skill。把执行留痕沉淀为可查的文档 / 决策记录 / 案例库。",
        "when_to_use": "任务完成、评审通过、或需要归档一次执行时。",
        "common_pitfalls": (
            "- 文档过于冗长，无法追溯关键决策。\n"
            "- 与既有文档重复。\n"
            "- 未建立索引。"
        ),
        "chk1": "文档结构统一，含关键决策与证据",
        "chk2": "已建立 / 更新索引",
        "chk3": "文档链接到相关快照与版本",
    },
    "pax-monitor": {
        "overview": "运行中监控与告警 Skill。持续观察执行状态、指标、错误，触发告警与升级。",
        "when_to_use": "长耗时执行、部署、数据订正等需要持续观察的任务。",
        "common_pitfalls": (
            "- 告警阈值过宽，问题被淹没。\n"
            "- 只监控不升级，异常无人响应。\n"
            "- 与运行中验证职责混淆。"
        ),
        "chk1": "监控指标与告警阈值明确",
        "chk2": "告警触发有升级路径",
        "chk3": "监控事件已留痕到快照",
    },
    "pax-rollback": {
        "overview": "自动化回滚 Skill。执行失败或出现严重异常时按预定策略回滚到安全状态。",
        "when_to_use": "执行失败、运行监控触发严重告警、或用户显式请求回滚。",
        "common_pitfalls": (
            "- 回滚策略未覆盖所有变更面。\n"
            "- 回滚未走审批。\n"
            "- 回滚失败后未告警。"
        ),
        "chk1": "回滚前已确认用户 approval / confirm",
        "chk2": "回滚策略覆盖所有变更面",
        "chk3": "回滚结果已留痕，失败路径已告警",
    },
    "pax-test": {
        "overview": "自动化测试生成 Skill。根据代码 / 契约生成测试用例，覆盖率不达标时补测。",
        "when_to_use": "新功能开发完成、契约变更后、或评审要求补测时。",
        "common_pitfalls": (
            "- 生成的测试用例覆盖不到边界条件。\n"
            "- 只测正向路径。\n"
            "- 未与 CI 集成。"
        ),
        "chk1": "测试覆盖正向 / 反向 / 边界三类路径",
        "chk2": "测试可在 CI 中稳定执行",
        "chk3": "覆盖率与验收标准对齐",
    },
    "pax-deploy": {
        "overview": "部署流程编排 Skill。按预定流水线编排部署，处理审批、健康检查、回滚。",
        "when_to_use": "任务完成评审、需要发布到目标环境时。高风险，需要用户显式 approval / confirm。",
        "common_pitfalls": (
            "- 跳过 approval / confirm 门禁直接部署。\n"
            "- 健康检查失败未阻断发布。\n"
            "- 未定义回滚路径。"
        ),
        "chk1": "已获得用户显式 approval / confirm",
        "chk2": "部署流水线包含健康检查与失败回滚",
        "chk3": "部署留痕完整，可以审计",
    },
    "pax-learn": {
        "overview": "经验沉淀与知识图谱 Skill。从执行留痕中提取经验，构建可复用的知识图谱。",
        "when_to_use": "大量执行留痕积累后、或自进化触发经验提取时。",
        "common_pitfalls": (
            "- 经验提取过于主观，缺乏证据。\n"
            "- 图谱条目重复。\n"
            "- 未与文档沉淀对齐。"
        ),
        "chk1": "经验提取有证据支撑",
        "chk2": "知识图谱条目去重",
        "chk3": "沉淀结果与文档沉淀索引一致",
    },
    "pax-init": {
        "overview": (
            "项目接入 Skill。扫描目标项目技术栈与既有规范文档，生成 AGENTS.md 与 "
            ".pax/project-profile.json，并创建 .pax/ 产物目录，供规划 / 执行 / 评审层消费。"
        ),
        "when_to_use": (
            "用户要求初始化项目 / 接入家族，或目标项目缺少 AGENTS.md 或 project-profile 时。"
            "直接调用型内部工具，不走编排路由。"
        ),
        "common_pitfalls": (
            "- 未确认项目路径就开始扫描，甚至为不存在的路径创建目录。\n"
            "- 技术栈靠猜而不看特征文件。\n"
            "- 直接覆盖目标项目已有的 AGENTS.md。\n"
            "- 把项目自有规范文档全文复制进 profile，造成双源漂移。"
        ),
        "chk1": "已声明模式、目标路径、扫描结果、AGENTS.md 处置与 .pax/ 状态",
        "chk2": "每项技术栈结论都能指向具体特征文件，未命中标「未检测到」",
        "chk3": "profile 与 AGENTS.md 摘要字段一致，且重复运行幂等",
    },
}

SKILLS_WITH_SHARED_REFERENCES = ("pax-clarify", "pax-orchestrate")


def _insert_sections(skill_md: Path, name: str) -> bool:
    """Insert the 4 recommended sections into skill_md. Return True if changed."""
    text = skill_md.read_text(encoding="utf-8")

    if SECTIONS_MARKER in text:
        return False

    data = SECTIONS_DATA.get(name)
    if data is None:
        print(f"  ! no section template for {name}; skipping")
        return False

    block = SECTIONS_TEMPLATE.format(**data)

    title_pattern = re.compile(rf"^(# {re.escape(name)}\s*)\n", re.MULTILINE)
    m = title_pattern.search(text)
    if m is None:
        m2 = re.search(r"^## ", text, re.MULTILINE)
        if m2 is None:
            text = text.rstrip() + "\n\n" + block
        else:
            text = text[: m2.start()] + block + "\n" + text[m2.start():]
    else:
        end = m.end()
        text = text[:end] + "\n" + block + text[end:]

    skill_md.write_text(text, encoding="utf-8")
    return True


def _prepend_trigger(skill_md: Path) -> bool:
    """Prepend 'Use when ...' to the description content if it does not
    already start with a trigger keyword.

    Handles the common YAML shape used in this family:
        description: >
          <chinese prose>
    """
    text = skill_md.read_text(encoding="utf-8")

    m = re.search(
        r"^description:\s*>\s*\n(\s+)([^\n]+)",
        text,
        re.MULTILINE,
    )
    if m is None:
        return False

    indent = m.group(1)
    first_line = m.group(2)
    if first_line.strip().lower().startswith(("use when", "when to use", "trigger")):
        return False

    new_line = f"{indent}Use when: {first_line}"
    new_text = text[: m.start(2)] + new_line + text[m.end(2):]
    skill_md.write_text(new_text, encoding="utf-8")
    return True


def _install_reference_copies() -> int:
    src = SHARED_REFERENCES / "domain-dependencies.md"
    if not src.exists():
        print(f"  ! missing shared reference: {src}")
        return 0
    count = 0
    for name in SKILLS_WITH_SHARED_REFERENCES:
        skill_dir = SKILLS_DIR / name
        if not skill_dir.is_dir():
            continue
        dst_dir = skill_dir / "references"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "domain-dependencies.md"
        if dst.exists():
            continue
        shutil.copyfile(src, dst)
        count += 1
    return count


def main() -> int:
    changed_sections = 0
    changed_triggers = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        if _insert_sections(skill_md, skill_dir.name):
            changed_sections += 1
        if _prepend_trigger(skill_md):
            changed_triggers += 1
    copies = _install_reference_copies()
    print(f"inserted sections:   {changed_sections}")
    print(f"prepended trigger:   {changed_triggers}")
    print(f"copied references:   {copies}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
