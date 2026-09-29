"""Cross-skill contract tests for pax-* family.

Every contract is a function ``(family_root: Path) -> list[str]`` returning
violation messages. Empty list = pass.
"""
from __future__ import annotations

import json as _json
import re as _re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import jsonschema

from pax.forge import loader
from pax.forge.validator import _split_frontmatter

ContractFn = Callable[[Path], list[str]]

_CONTRACTS: dict[str, ContractFn] = {}


def register_contract(name: str):
    def deco(fn: ContractFn) -> ContractFn:
        _CONTRACTS[name] = fn
        return fn
    return deco


def list_contracts() -> list[str]:
    return sorted(_CONTRACTS.keys())


@dataclass
class ContractReport:
    ok: bool = True
    failures: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    def add_pass(self, name: str) -> None:
        self.passes.append(name)

    def add_fail(self, name: str, messages: list[str]) -> None:
        self.ok = False
        for m in messages:
            self.failures.append(f"[{name}] {m}")


def run_all_contracts(family_root: Path) -> ContractReport:
    report = ContractReport()
    for name, fn in _CONTRACTS.items():
        try:
            violations = fn(family_root)
        except Exception as exc:
            report.add_fail(name, [f"contract raised: {exc!r}"])
            continue
        if violations:
            report.add_fail(name, violations)
        else:
            report.add_pass(name)
    return report


def _iter_skill_dirs(family_root: Path) -> Iterable[Path]:
    skills_dir = family_root / "skills"
    if not skills_dir.exists():
        return
    for child in skills_dir.iterdir():
        if child.is_dir() and (child / "SKILL.md").exists():
            yield child


# ----- 契约①：frontmatter 完整性 -----

@register_contract("frontmatter-completeness")
def check_frontmatter_completeness(family_root: Path) -> list[str]:
    violations: list[str] = []
    family = loader.load_family_schema()
    required = family["contracts"]["required_frontmatter"]
    naming_re = _re.compile(family["contracts"]["naming"])
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm is None:
            violations.append(
                f"{skill_dir.name}: invalid or missing frontmatter"
            )
            continue
        for key in required:
            if key not in fm:
                violations.append(
                    f"{skill_dir.name}: frontmatter missing '{key}'"
                )
        if not naming_re.match(fm.get("name", "")):
            violations.append(
                f"{skill_dir.name}: name violates naming contract"
            )
    return violations


# ----- 契约②：snapshot schema 合法性 -----

@register_contract("snapshot-schema-validity")
def check_snapshot_schema_validity(family_root: Path) -> list[str]:
    violations: list[str] = []
    schema_path = family_root / "schemas" / "snapshot.schema.json"
    if not schema_path.exists():
        return [f"missing {schema_path}"]
    with schema_path.open("r", encoding="utf-8") as f:
        schema = _json.load(f)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        violations.append(f"snapshot schema invalid: {exc.message}")
    return violations


# ----- 契约③：层间调用合法性 -----

def _allowed_calls() -> set[tuple[str, str]]:
    return {
        ("L0", "L1"),
        ("L1", "L1"),   # 相邻阶段
        ("L1", "L2"),
        ("L1", "L3"),
        ("L2", "L3"),
        ("L0", "L4"),
        ("L1", "L4"),
        ("L2", "L4"),
    }


@register_contract("layer-call-legality")
def check_layer_call_legality(family_root: Path) -> list[str]:
    allowed = _allowed_calls()
    violations: list[str] = []
    skill_layers: dict[str, str] = {}
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm and "name" in fm and "layer" in fm:
            skill_layers[fm["name"]] = fm["layer"]
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        self_layer = fm["layer"]
        mentioned = set(_re.findall(r"pax-[a-z][a-z0-9-]*", body))
        mentioned -= {fm["name"]}
        for target_name in mentioned:
            target_layer = skill_layers.get(target_name)
            if target_layer is None:
                continue
            if (self_layer, target_layer) not in allowed:
                violations.append(
                    f"{fm['name']} ({self_layer}) references "
                    f"{target_name} ({target_layer}): forbidden direction"
                )
    return violations


# ----- 契约④：版本一致性 -----

@register_contract("version-consistency")
def check_version_consistency(family_root: Path) -> list[str]:
    versions_path = family_root / "pax-ops" / "versions.json"
    if not versions_path.exists():
        return ["missing pax-ops/versions.json"]
    with versions_path.open("r", encoding="utf-8") as f:
        versions = _json.load(f)
    known = versions.get("skills", {})
    violations: list[str] = []
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm is None:
            continue
        name = fm.get("name")
        if name not in known:
            violations.append(
                f"{name}: not listed in pax-ops/versions.json"
            )
            continue
        if known[name].get("version") != fm.get("version"):
            violations.append(
                f"{name}: SKILL.md version {fm.get('version')!r} != "
                f"versions.json {known[name].get('version')!r}"
            )
    return violations


# ----- 契约⑤：无循环依赖 -----

def _extract_call_graph(family_root: Path) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        name = fm["name"]
        mentioned = set(_re.findall(r"pax-[a-z][a-z0-9-]*", body))
        mentioned -= {name}
        graph[name] = mentioned
    return graph


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    seen_global: set[tuple[str, ...]] = set()
    visited: set[str] = set()
    path: list[str] = []

    def dfs(node: str):
        if node in path:
            cyc = tuple(path[path.index(node):])
            if cyc not in seen_global:
                seen_global.add(cyc)
                cycles.append(list(cyc) + [node])
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for nxt in sorted(graph.get(node, ())):
            if nxt in graph:
                dfs(nxt)
        path.pop()

    for node in sorted(graph):
        visited.clear()
        path.clear()
        dfs(node)
    return cycles


@register_contract("no-cycles")
def check_no_cycles(family_root: Path) -> list[str]:
    graph = _extract_call_graph(family_root)
    cycles = _find_cycles(graph)
    return [f"cycle detected: {' -> '.join(c)}" for c in cycles]


# ----- 契约⑥：跳过审计 -----

SKIP_AUDIT_KEYWORDS = ("skip_reason", "跳过留痕", "跳过理由")


@register_contract("skip-audit")
def check_skip_audit(family_root: Path) -> list[str]:
    violations: list[str] = []
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        if not fm.get("optional", False):
            continue
        if not any(k in body for k in SKIP_AUDIT_KEYWORDS):
            violations.append(
                f"{fm['name']}: optional skill must document "
                f"skip_reason (跳过留痕契约)"
            )
    return violations


# ----- 契约⑦：门禁行为 -----

GATE_KEYWORDS = ("前置门禁", "前置条件", "未通过", "不满足", "禁止", "降级")


@register_contract("gate-behavior")
def check_gate_behavior(family_root: Path) -> list[str]:
    violations: list[str] = []
    for skill_dir in _iter_skill_dirs(family_root):
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        if fm is None:
            continue
        marker = "## Execution Contract"
        if marker not in body:
            violations.append(
                f"{fm['name']}: missing Execution Contract section"
            )
            continue
        section = body.split(marker, 1)[1]
        if "\n## " in section:
            section = section.split("\n## ", 1)[0]
        if not any(k in section for k in GATE_KEYWORDS):
            violations.append(
                f"{fm['name']}: Execution Contract lacks precondition/gate keyword"
            )
    return violations
