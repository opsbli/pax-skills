"""Generate pax-* skill skeletons from layered templates."""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from pax.forge import loader


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class GenerationError(Exception):
    pass


def _render(template_name: str, **ctx: object) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    return env.get_template(f"{template_name}.tmpl").render(**ctx)


def generate_skill(*, name: str, layer: str, description: str,
                   target_root: Path, optional: bool = False) -> Path:
    """Create `target_root/skills/<name>/SKILL.md` and return the skill dir."""
    family = loader.load_family_schema()
    naming_re = re.compile(family["contracts"]["naming"])
    if not naming_re.match(name):
        raise GenerationError(
            f"Name violates family naming contract: {name!r}"
        )
    versions = loader.load_versions()
    family_version = versions["version"]
    skill_version = versions["skills"].get(name, {}).get(
        "version", family_version
    )
    skill_dir = target_root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    template_name = "meta" if layer == "meta" else layer
    content = _render(
        template_name,
        name=name, layer=layer, description=description,
        optional=optional, version=skill_version,
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir
