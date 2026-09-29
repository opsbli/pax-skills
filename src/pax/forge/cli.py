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

    # version
    version_p = sub.add_parser("version", help="Bump family version")
    version_p.add_argument("bump", choices=["patch", "minor", "major"])

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
            )
        except GenerationError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {skill_dir}")
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

    # 所有子命令在后续 Task 中逐步实现；未实现时统一返回 2
    return _not_implemented()


if __name__ == "__main__":
    raise SystemExit(main())
