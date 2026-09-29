"""Declarative patch layer with idempotent replay.

A "patch" is a small dictionary describing an edit to a file under the
pax-* family root:

    {
        "id": "p1",                      # required by manifest replay
        "target": "skills/pax-clarify/SKILL.md",  # relative to family_root
        "operation": "replace" | "append" | "remove",
        "needle": "...",                 # required for replace/remove
        "repl": "..."                    # required for replace/append
    }

Idempotent semantics (``idempotent=True`` — default):
- replace: if needle absent, return False (no side effect, no error).
- append:  if text already ends with ``repl``, return False.
- remove:  if needle absent, return False.

Strict mode (``idempotent=False``) raises :class:`PatchError` for any
missing needle / missing target file so CI pipelines fail loudly.

``apply_manifest`` iterates the manifest's ``patches`` list, skips entries
whose ``id`` is already in ``applied``, runs each remaining patch in
idempotent mode, and writes the updated ``applied`` list back via the
loader. Returns the count of *newly* applied patches in this run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pax.forge import loader


class PatchError(Exception):
    """Raised when a patch cannot be applied (strict mode) or has an
    unknown operation."""


def apply_patch(
    patch: dict[str, Any],
    *,
    family_root: Path,
    idempotent: bool = True,
) -> bool:
    """Apply a single patch. Returns True if a change was made, else False.

    Parameters
    ----------
    patch:
        Dict with keys ``target``, ``operation`` and (as required by the
        operation) ``needle`` / ``repl``.
    family_root:
        Family root directory; ``target`` is resolved relative to it.
    idempotent:
        When True (default) missing needles are treated as "already
        applied" and the function returns False. When False, missing
        needles raise :class:`PatchError`.
    """
    op = patch.get("operation")
    target = family_root / patch["target"]

    if not target.exists():
        if idempotent:
            return False
        raise PatchError(f"target file missing: {target}")

    text = target.read_text(encoding="utf-8")

    if op == "replace":
        needle = patch["needle"]
        repl = patch["repl"]
        if needle not in text:
            if idempotent:
                return False
            raise PatchError(f"needle not found in {target}")
        target.write_text(text.replace(needle, repl, 1), encoding="utf-8")
        return True

    if op == "append":
        repl = patch["repl"]
        if text.endswith(repl):
            return False
        target.write_text(text + repl, encoding="utf-8")
        return True

    if op == "remove":
        needle = patch["needle"]
        if needle not in text:
            if idempotent:
                return False
            raise PatchError(f"needle not found for remove: {target}")
        target.write_text(text.replace(needle, "", 1), encoding="utf-8")
        return True

    raise PatchError(f"unknown operation: {op!r}")


def apply_manifest(*, family_root: Path) -> int:
    """Apply every patch in the manifest not yet in ``applied``.

    Returns the count of newly applied patches in this invocation. The
    ``applied`` list is persisted (sorted) so a subsequent call is a
    no-op unless the manifest grows with new patches.
    """
    manifest = loader.load_patches_manifest()
    already = set(manifest.get("applied", []))
    newly = 0

    for patch in manifest.get("patches", []):
        pid = patch.get("id")
        if pid is None:
            raise PatchError("patch entry missing 'id'")
        if pid in already:
            continue
        try:
            apply_patch(patch, family_root=family_root, idempotent=True)
        except PatchError as exc:
            raise PatchError(f"patch {pid!r} failed: {exc}") from exc
        already.add(pid)
        newly += 1

    manifest["applied"] = sorted(already)
    loader.save_patches_manifest(manifest)
    return newly
