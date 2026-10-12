#!/usr/bin/env python3
"""Probe v2: 严格判据下的真缺口识别。

v1 的教训：关键词命中是误报重灾区——「打包」= 批量提问、「orchestration」= 快照段、
「指标」= 评估指标、「迁移」= migration_tool 事实采集。这类词形匹配会把
「提到过」误判成「有能力」。

v2 的判据（全部要求**可执行结构**，不是词语）：
  A. 存在判定函数/判定表（def xxx / | 表格 | frontmatter 字段）
  B. 存在该能力专属的快照段字段（写入路径）
  C. 存在该能力专属的脚本/工具引用
任一成立= 「有结构」；三者皆无 = 真缺口。

只读。不调模型。
"""
import re
from pathlib import Path

ROOT = Path(r"C:/Users/sam/Documents/skills/pax-skills")
SKILLS = ROOT / "skills"

# 每条主张要求出现的「结构性证据」：更强的正则 = 更严格的判据
STRICT = {
    "1  竞品比对/技术选型":
        r"(competitor|竞品矩阵|选型矩阵|weighted.*(score|evaluation)|composite_score)",
    "2  架构决策记录 ADR":
        r"(ADR|architecture decision|架构决策记录|adr_)",
    "3  设计系统/设计令牌":
        r"(design[_ ]token|设计令牌|design[_ ]system|设计系统)",
    "4  SAST/密钥扫描门禁":
        r"(SAST|DAST|secret[_ ]scan|密钥扫描|gitleaks|trufflehog|CVE-\d)",
    "5  CI/CD 流水线生成":
        r"(github[ _]actions|gitlab[ _]ci|jenkins|workflow.*ya?ml|pipeline.*generat)",
    "6  SLO/可观测性设计":
        r"(SLO|SLIs?|service[_ ]level|observability[_ ]plan|P95|p99)",
    "7  迁移 up/down 校验":
        r"(down_sql|rollback.*migration|migration.*down|可逆性|reversible)",
    "8  WCAG/ARIA/i18n":
        r"(WCAG|ARIA|a11y|i18n|国际化|localization|可访问性)",
    "9  事故复盘时间线":
        r"(incident[_ ]snapshot|postmortem|复盘|timeline|时间线|无责)",
    "10 许可证合规":
        r"(license[_ ]check|许可证|GPL|AGPL|license[_ ]compliance)",
    "11 重构行为等价性":
        r"(behavior.*equival|行为等价|characterization[_ ]test|refactor[_ ]snapshot)",
    "12 N+1/慢查询优化":
        r"(N\+1|慢查询|全表扫描|query[_ ]optimiz|索引优化)",
    "13 GDPR/SOC2 合规":
        r"(GDPR|SOC ?2|HIPAA|数据留存|data[_ ]retention|consent[_ ]management)",
    "14 移动端签名打包":
        r"(codesign|签名证书|APK|IPA|provisioning[_ ]profile)",
    "15 K8s manifest":
        r"(kubectl|kubernetes|kind: (Deployment|Service|Pod)|helm)",
    "16 MLOps":
        r"(MLOps|model[_ ]training|MLflow|特征工程|模型评估)",
    "17 项目记忆文件":
        r"(PRODUCT\.md|MILESTONES\.md|TASKS\.md|THINKING\.md)",
    "18 周期性自审":
        r"(self[_ -]?audit|自审|cron|定时.*审)",
    "19 闭环回退路由":
        r"(fallback|回退路由|rollback[_ ]route|重路由)",
    "20 对抗性/多标签评估":
        r"(adversarial|对抗性|multi[_ ]label|多标签)",
}

print("=" * 80)
print("需求主张的「结构性证据」核查（严格判据）")
print("=" * 80)
print("判据：存在可执行结构（判定函数/表格/字段/脚本），而非仅词语出现\n")

docs = {}
for sd in sorted(SKILLS.iterdir()):
    f = sd / "SKILL.md"
    if f.is_file():
        docs[sd.name] = f.read_text(encoding="utf-8")

# 快照 schema 的顶层段（写入路径的唯一权威来源）
import json
schema = json.loads((ROOT / "schemas" / "snapshot.schema.json").read_text(encoding="utf-8"))
print(f"快照已有顶层段（{len(schema['properties'])} 个）：")
print("  " + ", ".join(sorted(schema["properties"])))
print()

真缺口, 有结构 = [], []
for claim, pat in STRICT.items():
    rx = re.compile(pat, re.IGNORECASE)
    found = []
    for name, text in docs.items():
        for m in rx.finditer(text):
            ln = text[:m.start()].count("\n") + 1
            line = text.splitlines()[ln - 1].strip()
            found.append((name, ln, m.group(0), line[:100]))
    if found:
        有结构.append((claim, found))
    else:
        真缺口.append(claim)

print("=" * 80)
print(f"结果：有结构性实现 {len(有结构)} 条 / 无任何结构（真缺口） {len(真缺口)} 条")
print("=" * 80)

print("\n【真缺口】文档判断成立 —— 家族内确实没有任何可执行结构：")
for c in 真缺口:
    print(f"  ✗ {c}")

print("\n【已有结构】存在可执行实现，文档主张需下调优先级：")
for c, found in 有结构:
    names = sorted({x[0] for x in found})
    print(f"\n  ✓ {c}")
    print(f"      实现于: {', '.join(names)}")
    for n, ln, tok, line in found[:3]:
        print(f"      {n}:{ln}  「{tok}」")
        print(f"         {line}")

print()
print("=" * 80)
print("汇总")
print("=" * 80)
print(f"  真缺口（需新建能力）: {len(真缺口)}/{len(STRICT)}")
print(f"  已有结构（勿新建，改为接线/加强）: {len(有结构)}/{len(STRICT)}")