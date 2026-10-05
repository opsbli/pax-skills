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
                   target_root: Path, optional: bool = False,
                   use_case: str | None = None) -> Path:
    """Create `target_root/skills/<name>/SKILL.md` and return the skill dir.

    The family's schema/version source is resolved from ``target_root`` when
    that directory already owns them (the ``init`` → ``new`` flow). Otherwise
    the tool's own family is used, so a bare target directory still gets a
    valid skeleton.
    """
    family_root = loader.resolve_family_root(target_root)
    family = loader.load_family_schema(family_root=family_root)
    naming_re = re.compile(family["contracts"]["naming"])
    if not naming_re.match(name):
        raise GenerationError(
            f"Name violates family naming contract: {name!r}"
        )
    versions = loader.load_versions(family_root=family_root)
    family_version = versions["version"]
    skill_version = versions["skills"].get(name, {}).get(
        "version", family_version
    )
    skill_dir = target_root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    template_name = "meta" if layer == "meta" else layer
    ctx: dict[str, object] = dict(
        name=name, layer=layer, description=description,
        optional=optional, version=skill_version,
    )
    # Only pass use_case when supplied: the template's `default` filter
    # handles the undefined case, but passing None would render "None".
    if use_case:
        ctx["use_case"] = use_case
    content = _render(template_name, **ctx)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir
