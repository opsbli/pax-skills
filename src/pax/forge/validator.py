"""Validate a single pax-* skill directory against family contracts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pax.forge import loader


@dataclass
class ValidationReport:
    path: Path
    ok: bool
    violations: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.violations.append(msg)
        self.ok = False


def _split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split YAML frontmatter from body. Returns (None, text) if absent."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, text
    if not isinstance(fm, dict):
        return None, text
    return fm, parts[2]


def validate_skill(skill_dir: Path) -> ValidationReport:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ValidationReport(skill_md, False, ["SKILL.md missing"])
    text = skill_md.read_text(encoding="utf-8")
    family = loader.load_family_schema()
    contracts = family["contracts"]

    fm, body = _split_frontmatter(text)
    if fm is None:
        return ValidationReport(skill_md, False,
                                ["Invalid or missing YAML frontmatter"])

    report = ValidationReport(skill_md, True)
    if not re.match(contracts["naming"], fm.get("name", "")):
        report.add(f"frontmatter.name violates naming: {fm.get('name')!r}")
    for key in contracts["required_frontmatter"]:
        if key not in fm:
            report.add(f"frontmatter missing required key: {key}")
    for section in contracts["required_sections"]:
        if f"## {section}" not in body:
            report.add(f"missing required section: {section}")
    return report
