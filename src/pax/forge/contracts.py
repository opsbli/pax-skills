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
