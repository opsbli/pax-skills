"""Version management helpers for the pax-* family.

Three concerns:
1. Pure ``bump_version`` arithmetic (major/minor/patch).
2. ``apply_bump`` writes the result to ``pax-ops/versions.json``.
3. ``list_version`` reads the package version from ``pax/__init__.py``;
   ``check_registry_versions`` cross-checks every ``skills/*/SKILL.md``
   frontmatter against ``versions.json``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pax.forge import loader
from pax.forge.validator import _split_frontmatter


class VersionError(Exception):
    """Raised for malformed version strings or invalid operations."""


_VERSION_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def bump_version(current: str, bump: str) -> str:
    """Return the new semver string after applying ``bump`` to ``current``."""
    parts = current.split(".")
    if len(parts) != 3:
        raise VersionError(
            f"expected MAJOR.MINOR.PATCH, got {current!r}"
        )
    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError as exc:
        raise VersionError(
            f"expected numeric segments, got {current!r}"
        ) from exc
    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = patch = 0
    else:
        raise VersionError(f"unknown bump: {bump}")
    return f"{major}.{minor}.{patch}"


def apply_bump(bump: str, *, family_only: bool = False) -> str:
    """Bump the family version and write it back to ``versions.json``.

    When ``family_only`` is False, every registered skill's version is
    bumped to the new family version (mirrors the plan's default
    behaviour).  When True, only the top-level ``version`` field changes.
    """
    versions = loader.load_versions()
    new = bump_version(versions["version"], bump)
    versions["version"] = new
    if not family_only:
        for name in versions.get("skills", {}):
            versions["skills"][name]["version"] = new
    with loader.VERSIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return new


def deprecate_skill(name: str) -> None:
    """Mark a skill as ``deprecated`` in ``versions.json``."""
    versions = loader.load_versions()
    if name not in versions.get("skills", {}):
        raise VersionError(f"skill not in versions.json: {name}")
    versions["skills"][name]["status"] = "deprecated"
    with loader.VERSIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)
        f.write("\n")


def list_version() -> str:
    """Return the package version declared in ``pax/__init__.py``.

    Reads the source file (rather than importing ``pax``) so that CLI
    output reflects the file on disk even after ``apply_bump`` bumps the
    family version without a corresponding package-level bump.
    """
    init_path = Path(__file__).resolve().parent.parent / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    m = _VERSION_RE.search(text)
    if not m:
        raise VersionError(f"__version__ not found in {init_path}")
    return m.group(1)


def check_registry_versions(root: Path) -> list[str]:
    """Return mismatches between ``SKILL.md`` and ``versions.json``.

    For every ``skills/<name>/SKILL.md``, compare ``frontmatter.version``
    against ``versions.json["skills"][name]["version"]``.  Directories
    without a ``SKILL.md`` (or not listed in ``versions.json``) are
    skipped silently — the frontmatter-completeness contract is
    responsible for those checks.
    """
    mismatches: list[str] = []
    versions = loader.load_versions()
    skills = versions.get("skills", {})
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(text)
        if fm is None:
            mismatches.append(
                f"{skill_dir.name}: invalid frontmatter, "
                f"cannot read version"
            )
            continue
        skill_ver = str(fm.get("version", ""))
        expected = skills.get(skill_dir.name, {}).get("version")
        if expected is None:
            continue  # not tracked in versions.json; not our concern
        if skill_ver != expected:
            mismatches.append(
                f"{skill_dir.name}: SKILL.md={skill_ver}, "
                f"versions.json={expected}"
            )
    return mismatches
