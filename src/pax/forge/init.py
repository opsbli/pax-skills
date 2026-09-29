"""Generate pax-* family skeleton into a target directory."""
from __future__ import annotations

import shutil
from pathlib import Path

from pax.forge import loader


SKELETON_FILES: dict[str, Path] = {
    "schemas/pax-family.schema.yaml": loader.FAMILY_SCHEMA_PATH,
    "schemas/snapshot.schema.json": loader.SNAPSHOT_SCHEMA_PATH,
    "pax-ops/versions.json": loader.VERSIONS_PATH,
    "pax-ops/registry.json": loader.REGISTRY_PATH,
    "pax-ops/patches/manifest.json": loader.PATCHES_MANIFEST_PATH,
}

SKELETON_DIRS: list[str] = ["skills", "references"]


class InitError(Exception):
    pass


def init_family(target: Path) -> list[Path]:
    """Copy single-source-of-truth files into `target` and create empty dirs."""
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise InitError(f"Target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    for d in SKELETON_DIRS:
        (target / d).mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for rel, src in SKELETON_FILES.items():
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(dst)
    return copied
