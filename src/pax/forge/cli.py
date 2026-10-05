"""pax-forge CLI: generator, validator, contract tester."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pax import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pax-forge",
        description="pax-* family: generator, validator, contract tester",
    )
    parser.add_argument("--version", action="version",
                        version=f"pax-forge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    init_p = sub.add_parser("init", help="Generate pax-* family skeleton")
    init_p.add_argument("path", nargs="?", default="./pax-family",
                        help="Target directory")

    # new
    new_p = sub.add_parser("new", help="Create a new pax-* skill")
    new_p.add_argument("name")
    new_p.add_argument("--layer", required=True,
                       choices=["meta", "L0", "L1", "L2", "L3", "L4"])
    new_p.add_argument("--description", default="TODO: describe capability")
    new_p.add_argument(
        "--use-case", default=None,
        help="One-line 'when to use this skill' phrase for the description body",
    )
    new_p.add_argument("--optional", action="store_true")

    # validate
    validate_p = sub.add_parser("validate", help="Validate a single skill directory")
    validate_p.add_argument("path")

    # register
    register_p = sub.add_parser("register", help="Register a validated skill")
    register_p.add_argument("path")

    # list
    sub.add_parser("list", help="List registered skills")

    # test
    test_p = sub.add_parser("test", help="Run cross-skill contract tests")
    test_p.add_argument("--skill", help="Only test this skill (default: all)")

    # agentskills-ci wrapper
    ci_p = sub.add_parser(
        "agentskills-ci",
        help=(
            "Run the agentskills-ci scorer against the skills/ directory. "
            "Fails (exit 1) if any skill is below --min-score or has an "
            "error-severity issue."
        ),
    )
    ci_p.add_argument(
        "--skills-dir", default="./skills",
        help="Directory containing skill subdirectories (default: ./skills)",
    )
    ci_p.add_argument(
        "--min-score", type=int, default=80,
        help="Minimum required score per skill (default: 80)",
    )
    ci_p.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    ci_p.add_argument(
        "-o", "--output",
        help="Write report to this file (in addition to stdout)",
    )
    ci_p.add_argument(
        "--json-only", action="store_true",
        help="Print JSON output only (silences the human-readable summary)",
    )

    # version
    version_p = sub.add_parser(
        "version",
        help="Bump family version, or inspect versions",
    )
    version_p.add_argument(
        "bump", choices=["patch", "minor", "major"], nargs="?",
        default=None,
    )
    version_p.add_argument(
        "--list", action="store_true",
        help="Print the current pax.__version__ from __init__.py",
    )
    version_p.add_argument(
        "--check-registry", action="store_true",
        help="Verify skills/*/SKILL.md versions match versions.json",
    )

    # deprecate
    deprecate_p = sub.add_parser("deprecate", help="Mark a skill as deprecated")
    deprecate_p.add_argument("name")

    # patch
    patch_p = sub.add_parser("patch", help="Apply declarative patches")
    patch_sub = patch_p.add_subparsers(dest="sub_command", required=True)
    patch_sub.add_parser("apply", help="Replay patches manifest idempotently")

    return parser


def _not_implemented() -> int:
    print("(subcommand not yet implemented)", file=sys.stderr)
    return 2


def _run_agentskills_ci(args: argparse.Namespace) -> int:
    """Delegate to the external agentskills-ci scorer.

    The tool is installed as a pip dependency (`pip install agentskills-ci`)
    and is vendored under `tools/agentskills-ci/` for local development only.
    We shell out rather than importing so this CLI works in CI after the
    standard `pip install agentskills-ci` step without any import path shim.

    Lookup order:
      1. `agentskills-ci` on PATH (typical after `pip install` in Linux/macOS)
      2. `agentskills-ci.exe` on PATH (Windows)
      3. `python -c "from agentskills_ci.cli import main; main([...])"`
         (covers the case where the console-script shim isn't on PATH yet)
    """
    import json
    import shutil
    import subprocess
    import sys as _sys

    skills_dir = Path(args.skills_dir)
    if not skills_dir.is_dir():
        print(f"error: skills directory not found: {skills_dir}",
              file=_sys.stderr)
        return 2

    inner_args = [
        "score", str(skills_dir),
        "--min-score", str(args.min_score),
        "--format", args.format,
    ]
    if args.output:
        inner_args.extend(["-o", str(args.output)])

    binary = shutil.which("agentskills-ci") or shutil.which("agentskills-ci.exe")

    if args.json_only:
        # Emit machine-readable output; hide all human-readable chatter.
        if binary:
            result = subprocess.run(
                [binary, *inner_args],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
        else:
            script = (
                "import sys; from agentskills_ci.cli import main; "
                "sys.exit(main(sys.argv[1:]))"
            )
            result = subprocess.run(
                [_sys.executable, "-c", script, *inner_args],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
        if result.stdout:
            _sys.stdout.write(result.stdout)
        if result.stderr:
            _sys.stderr.write(result.stderr)
        return result.returncode

    if binary:
        print(f"$ {' '.join([binary, *inner_args])}")
        return subprocess.run([binary, *inner_args]).returncode

    # Fallback: invoke the CLI module directly with the same interpreter.
    print("# agentskills-ci not found on PATH; invoking via python -m")
    script = (
        "import sys; from agentskills_ci.cli import main; "
        "sys.exit(main(sys.argv[1:]))"
    )
    return subprocess.run(
        [_sys.executable, "-c", script, *inner_args],
        text=True, encoding="utf-8", errors="replace",
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new":
        from pax.forge.generator import GenerationError, generate_skill
        try:
            skill_dir = generate_skill(
                name=args.name, layer=args.layer,
                description=args.description,
                target_root=Path.cwd(), optional=args.optional,
                use_case=args.use_case,
            )
        except GenerationError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {skill_dir}")
        return 0

    if args.command == "validate":
        from pax.forge.validator import validate_skill
        report = validate_skill(Path(args.path))
        if report.ok:
            print(f"OK  {report.path}")
            return 0
        print(f"FAIL {report.path}")
        for v in report.violations:
            print(f"  - {v}")
        return 1

    if args.command == "register":
        from pax.forge.validator import validate_skill
        from pax.forge.register import (
            AlreadyRegisteredError,
            _utc_now_iso,
            register_skill,
        )
        import yaml

        skill_dir = Path(args.path)
        report = validate_skill(skill_dir)
        if not report.ok:
            print("FAIL: skill did not validate", file=sys.stderr)
            for v in report.violations:
                print(f"  - {v}", file=sys.stderr)
            return 1
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(text.split("---", 2)[1])
        entry = {
            "name": fm["name"],
            "layer": fm["layer"],
            "optional": bool(fm.get("optional", False)),
            "version": fm.get("version", "0.1.0"),
            "path": f"skills/{fm['name']}/SKILL.md",
            "registered_at": _utc_now_iso(),
        }
        try:
            register_skill(entry)
        except AlreadyRegisteredError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"registered {entry['name']} @ {entry['version']}")
        return 0

    if args.command == "init":
        from pax.forge.init import init_family, InitError
        target = Path(args.path).resolve()
        try:
            copied = init_family(target)
        except InitError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for p in copied:
            print(f"  wrote {p.relative_to(target)}")
        print(f"init complete -> {target}")
        return 0

    if args.command == "list":
        from pax.forge import loader
        registry = loader.load_registry()
        skills = registry.get("skills", [])
        if not skills:
            print("(empty registry)")
            return 0
        print(f"{len(skills)} skills:")
        for s in skills:
            opt = " (optional)" if s.get("optional") else ""
            print(f"  {s['name']}@{s['version']}  [{s['layer']}]{opt}")
        return 0

    if args.command == "test":
        from pax.forge.contracts import run_all_contracts, list_contracts
        root = Path.cwd()
        report = run_all_contracts(root)
        print(f"contracts discovered: {', '.join(list_contracts()) or '(none)'}")
        for p in report.passes:
            print(f"  PASS  {p}")
        for f in report.failures:
            print(f"  FAIL  {f}")
        print(f"\n{len(report.passes)} passed, {len(report.failures)} failed")
        return 0 if report.ok else 1

    if args.command == "agentskills-ci":
        return _run_agentskills_ci(args)


    if args.command == "version":
        from pax.forge.versioning import (
            VersionError,
            apply_bump,
            check_registry_versions,
            list_version,
        )
        if args.list:
            print(list_version())
            return 0
        if args.check_registry:
            mismatches = check_registry_versions(Path.cwd())
            if not mismatches:
                print("all skills versions match versions.json")
                return 0
            print("version mismatches:")
            for m in mismatches:
                print(f"  - {m}")
            return 1
        if args.bump is None:
            print(
                "error: specify a bump (patch|minor|major) or use "
                "--list / --check-registry",
                file=sys.stderr,
            )
            return 2
        try:
            new = apply_bump(args.bump, family_only=False)
        except VersionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"bumped family to {new}")
        return 0

    if args.command == "deprecate":
        from pax.forge.versioning import VersionError, deprecate_skill
        try:
            deprecate_skill(args.name)
        except VersionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"deprecated {args.name}")
        return 0

    if args.command == "patch" and args.sub_command == "apply":
        from pax.forge.patcher import PatchError, apply_manifest
        try:
            n = apply_manifest(family_root=Path.cwd())
        except PatchError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"applied {n} new patches")
        return 0

    # 所有子命令在后续 Task 中逐步实现；未实现时统一返回 2
    return _not_implemented()


if __name__ == "__main__":
    raise SystemExit(main())
