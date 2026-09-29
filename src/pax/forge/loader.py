"""Load pax-* family single-source-of-truth files."""
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


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_family_schema(path: Path | None = None) -> dict[str, Any]:
    """Load family schema. ``path=None`` resolves FAMILY_SCHEMA_PATH at call
    time so tests can monkeypatch the module attribute."""
    if path is None:
        path = FAMILY_SCHEMA_PATH
    return _load_yaml(path)


def load_snapshot_schema(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = SNAPSHOT_SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_versions(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = VERSIONS_PATH
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_registry(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = REGISTRY_PATH
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry: dict[str, Any], path: Path | None = None) -> None:
    if path is None:
        path = REGISTRY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_patches_manifest(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = PATCHES_MANIFEST_PATH
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_patches_manifest(
    manifest: dict[str, Any], path: Path | None = None
) -> None:
    if path is None:
        path = PATCHES_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
