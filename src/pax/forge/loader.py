"""Load pax-* family single-source-of-truth files.

Root resolution
---------------
Every loader accepts an optional ``family_root``. When given, the family's
schema / versions / registry are read from *that* directory — which is what
``pax-forge init <dir>`` followed by in-directory ``new``/``validate``/``test``
requires. When omitted, the repository that the tool is installed from
(``PAX_ROOT``) is used, so the CLI keeps working from anywhere on a single
checkout.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

# 仓库根：src/pax/forge/loader.py -> src/pax/forge -> src/pax -> src -> root
PAX_ROOT = Path(__file__).resolve().parents[3]

FAMILY_SCHEMA_PATH = PAX_ROOT / "schemas" / "pax-family.schema.yaml"
SNAPSHOT_SCHEMA_PATH = PAX_ROOT / "schemas" / "snapshot.schema.json"
VERSIONS_PATH = PAX_ROOT / "pax-ops" / "versions.json"
REGISTRY_PATH = PAX_ROOT / "pax-ops" / "registry.json"
PATCHES_MANIFEST_PATH = PAX_ROOT / "pax-ops" / "patches" / "manifest.json"

_FAMILY_SCHEMA_REL = Path("schemas") / "pax-family.schema.yaml"
_SNAPSHOT_SCHEMA_REL = Path("schemas") / "snapshot.schema.json"
_VERSIONS_REL = Path("pax-ops") / "versions.json"
_REGISTRY_REL = Path("pax-ops") / "registry.json"
_PATCHES_REL = Path("pax-ops") / "patches" / "manifest.json"


def family_paths(family_root: Path | None = None) -> dict[str, Path]:
    """Resolve every single-source-of-truth path for one family root."""
    root = Path(family_root) if family_root is not None else PAX_ROOT
    return {
        "family_schema": root / _FAMILY_SCHEMA_REL,
        "snapshot_schema": root / _SNAPSHOT_SCHEMA_REL,
        "versions": root / _VERSIONS_REL,
        "registry": root / _REGISTRY_REL,
        "patches_manifest": root / _PATCHES_REL,
    }


def resolve_family_root(candidate: Path | None) -> Path | None:
    """Return ``candidate`` if it looks like a family root, else ``None``.

    "Looks like a family root" = it owns the family schema or the version
    source. When it does not (e.g. ``pax-forge new --target`` pointed at a
    bare directory in a unit test), callers fall back to ``PAX_ROOT`` so the
    tool's own family still supplies the naming/section contracts.
    """
    if candidate is None:
        return None
    root = Path(candidate)
    if (root / _FAMILY_SCHEMA_REL).exists() or (root / _VERSIONS_REL).exists():
        return root
    return None


def _resolve(path: Path | None, module_default: Path,
             family_root: Path | None, rel: Path) -> Path:
    if path is not None:
        return path
    if family_root is not None:
        return Path(family_root) / rel
    return module_default


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_family_schema(path: Path | None = None,
                       family_root: Path | None = None) -> dict[str, Any]:
    """Load family schema. ``path=None`` resolves FAMILY_SCHEMA_PATH at call
    time so tests can monkeypatch the module attribute."""
    return _load_yaml(
        _resolve(path, FAMILY_SCHEMA_PATH, family_root, _FAMILY_SCHEMA_REL)
    )


def load_snapshot_schema(path: Path | None = None,
                         family_root: Path | None = None) -> dict[str, Any]:
    return _load_json(
        _resolve(path, SNAPSHOT_SCHEMA_PATH, family_root, _SNAPSHOT_SCHEMA_REL)
    )


def load_versions(path: Path | None = None,
                  family_root: Path | None = None) -> dict[str, Any]:
    return _load_json(
        _resolve(path, VERSIONS_PATH, family_root, _VERSIONS_REL)
    )


def load_registry(path: Path | None = None,
                  family_root: Path | None = None) -> dict[str, Any]:
    return _load_json(
        _resolve(path, REGISTRY_PATH, family_root, _REGISTRY_REL)
    )


def save_registry(registry: dict[str, Any], path: Path | None = None) -> None:
    target = path if path is not None else REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_patches_manifest(path: Path | None = None,
                          family_root: Path | None = None) -> dict[str, Any]:
    return _load_json(
        _resolve(path, PATCHES_MANIFEST_PATH, family_root, _PATCHES_REL)
    )


def save_patches_manifest(manifest: dict[str, Any],
                          path: Path | None = None) -> None:
    target = path if path is not None else PATCHES_MANIFEST_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
