"""Register a validated skill into pax-ops/registry.json."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pax.forge import loader


class AlreadyRegisteredError(Exception):
    """Raised when an entry with the same name is already in the registry."""


def _utc_now_iso() -> str:
    """Return a UTC ISO-8601 timestamp with 'Z' suffix and no microseconds."""
    return (datetime.now(timezone.utc).replace(microsecond=0)
            .isoformat().replace("+00:00", "Z"))


def register_skill(entry: dict[str, Any]) -> None:
    """Append ``entry`` to the family registry.

    - ``name`` is required and must be unique within the registry.
    - ``registered_at`` defaults to the current UTC timestamp when absent.
    - The registry's ``updated_at`` field is set to the entry's timestamp.
    """
    if "name" not in entry:
        raise ValueError("entry must contain 'name'")
    registry = loader.load_registry()
    for existing in registry.get("skills", []):
        if existing.get("name") == entry["name"]:
            raise AlreadyRegisteredError(
                f"{entry['name']} already registered"
            )
    entry = dict(entry)
    entry.setdefault("registered_at", _utc_now_iso())
    registry["skills"].append(entry)
    registry["updated_at"] = entry["registered_at"]
    loader.save_registry(registry)
