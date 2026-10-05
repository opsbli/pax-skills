#!/usr/bin/env python3
"""pax-init 确定性项目扫描器（stdlib-only，无网络、无副作用）。

用途：为 `pax-init` 的工作流 W2–W4 提供**确定性扫描证据**。扫描规则单一事实源是
`../references/tech-stack-detection.md`；本脚本只做「特征文件是否存在 + 能提取到什么」，
不做任何推测——未命中一律标为「未检测到」。

用法：
    python scripts/scan_project.py <项目根路径> [--frontend <前端路径>]

输出：JSON（stdout）。字段与 `.pax/project-profile.json` 对齐，可直接供 W5/W6 渲染使用。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NOT_DETECTED = "未检测到"

_NOISE_DIRS = {
    "node_modules", ".git", ".idea", ".vscode", "target", "build", "dist",
    "out", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
}

_ENTRY_CANDIDATES = [
    "manage.py", "app.py", "main.py", "src/main.ts", "src/main.js",
    "src/index.ts", "src/index.js", "index.js", "cmd/main.go",
]


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _first_match(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def _load_package_json(root: Path) -> dict:
    raw = _read(root / "package.json")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _deps(pkg: dict) -> dict:
    deps: dict = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = pkg.get(key)
        if isinstance(block, dict):
            deps.update(block)
    return deps


def _find_dep(deps: dict, needle: str) -> tuple[str, str] | None:
    """返回第一个名字含 needle 的依赖 (name, version)。"""
    for name, version in sorted(deps.items()):
        if needle in name:
            return name, str(version)
    return None


def _present(target: str, evidence: Path, extracted) -> dict:
    return {"target": target, "evidence_file": str(evidence), "extracted": extracted}


def _absent(target: str) -> dict:
    return {"target": target, "evidence_file": None, "extracted": NOT_DETECTED}


def detect_package_manager(root: Path) -> tuple[str, str]:
    """按优先级 pnpm > yarn > npm > 未检测到 返回 (manager, note)。"""
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm", ""
    if (root / "yarn.lock").exists():
        return "yarn", ""
    if (root / "package-lock.json").exists():
        note = ""
        for other in ("pnpm-lock.yaml", "yarn.lock"):
            if (root / other).exists():
                note = f"同时存在 {other}，lock 可能为历史遗留，已交用户确认"
        return "npm", note
    if (root / "package.json").exists():
        return NOT_DETECTED, "仅有 package.json 无 lock 文件，按规则标未检测到"
    return "", ""


def scan_tech_stack(root: Path) -> list[dict]:
    findings: list[dict] = []

    # 1 / 3 Java·Maven + Spring Boot
    pom = root / "pom.xml"
    if pom.exists():
        text = _read(pom)
        findings.append(_present("Java / Maven", pom, {
            "java_version": _first_match(
                r"<java\.version>([^<]+)</java\.version>", text),
            "group_id": _first_match(r"<groupId>([^<]+)</groupId>", text),
            "artifact_id": _first_match(r"<artifactId>([^<]+)</artifactId>", text),
            "modules": re.findall(r"<module>([^<]+)</module>", text),
        }))
        if "spring-boot-starter" in text:
            findings.append(_present("Spring Boot", pom, {
                "starters": sorted(set(re.findall(
                    r"<artifactId>(spring-boot-starter[^<]*)</artifactId>", text))),
            }))
        else:
            findings.append(_absent("Spring Boot"))
    else:
        findings.append(_absent("Java / Maven"))
        findings.append(_absent("Spring Boot"))

    # 2 Java·Gradle
    gradle = next((p for p in (root / "build.gradle", root / "build.gradle.kts")
                   if p.exists()), None)
    if gradle is not None:
        findings.append(_present("Java / Gradle", gradle, {
            "source_compatibility": _first_match(
                r"sourceCompatibility\s*=?\s*['\"]?([\w.]+)", _read(gradle)),
        }))
    else:
        findings.append(_absent("Java / Gradle"))

    # 4 RuoYi（目录含 ruoyi-* 模块）
    ruoyi = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and p.name.startswith("ruoyi-")) if root.is_dir() else []
    if ruoyi:
        generator = next((m for m in ruoyi if "generator" in m), NOT_DETECTED)
        findings.append(_present("RuoYi 框架", root, {
            "modules": ruoyi, "code_generator": generator}))
    else:
        findings.append(_absent("RuoYi 框架"))

    # 5–12 前端
    pkg = _load_package_json(root)
    deps = _deps(pkg)
    has_pkg = (root / "package.json").exists()

    tsconfig = root / "tsconfig.json"
    if tsconfig.exists():
        findings.append(_present("TypeScript", tsconfig,
                                 {"ts_version": deps.get("typescript", NOT_DETECTED)}))
    else:
        findings.append(_absent("TypeScript"))

    vite = next((p for p in (root / "vite.config.ts", root / "vite.config.js")
                 if p.exists()), None)
    if vite is not None:
        findings.append(_present("Vite", vite,
                                 {"vite_version": deps.get("vite", NOT_DETECTED)}))
    else:
        findings.append(_absent("Vite"))

    dep_rules = [
        ("Vue", "vue"),
        ("React", "react"),
        ("Element Plus", "element-plus"),
        ("Ant Design", "ant-design"),
        ("Pinia / Vuex", "pinia"),
    ]
    for label, needle in dep_rules:
        hit = _find_dep(deps, needle)
        if hit is None and needle == "pinia":
            hit = _find_dep(deps, "vuex")
        if hit is not None and has_pkg:
            findings.append(_present(label, root / "package.json",
                                     {"package": hit[0], "version": hit[1]}))
        else:
            findings.append(_absent(label))

    css = {n: str(v) for n, v in sorted(deps.items())
           if "unocss" in n or "tailwindcss" in n}
    if css and has_pkg:
        findings.append(_present("UnoCSS / Tailwind", root / "package.json", css))
    else:
        findings.append(_absent("UnoCSS / Tailwind"))

    # 13 Go
    go_mod = root / "go.mod"
    if go_mod.exists():
        blob = _read(go_mod)
        findings.append(_present("Go", go_mod, {
            "go_version": _first_match(r"^go\s+([\d.]+)", blob),
            "frameworks": [f for f in ("gin", "echo", "fiber") if f in blob.lower()],
        }))
    else:
        findings.append(_absent("Go"))

    # 14 Python
    py_manifests = [p for p in (root / "requirements.txt", root / "pyproject.toml")
                    if p.exists()]
    if py_manifests:
        blob = "\n".join(_read(p) for p in py_manifests).lower()
        findings.append(_present("Python", py_manifests[0], {
            "manifest_files": [str(p) for p in py_manifests],
            "frameworks": [f for f in ("django", "fastapi", "flask") if f in blob],
        }))
    else:
        findings.append(_absent("Python"))

    # 15 Node.js + 包管理器
    if has_pkg:
        manager, note = detect_package_manager(root)
        engines = pkg.get("engines") if isinstance(pkg.get("engines"), dict) else {}
        findings.append(_present("Node.js", root / "package.json", {
            "node_engine": engines.get("node", NOT_DETECTED),
            "package_manager": manager,
            "package_manager_note": note,
        }))
    else:
        findings.append(_absent("Node.js"))

    # 16 Docker
    docker = next((p for p in (root / "Dockerfile", root / "docker-compose.yml",
                               root / "docker-compose.yaml") if p.exists()), None)
    if docker is not None:
        findings.append(_present("Docker", docker, {
            "base_images": re.findall(r"^FROM\s+(\S+)", _read(docker), re.MULTILINE)}))
    else:
        findings.append(_absent("Docker"))

    # 17 CI/CD
    ci = None
    if (root / "Jenkinsfile").exists():
        ci = root / "Jenkinsfile"
    elif (root / ".github" / "workflows").is_dir():
        ci = root / ".github" / "workflows"
    if ci is not None:
        findings.append(_present("CI/CD", ci, {"tool": ci.name}))
    else:
        findings.append(_absent("CI/CD"))

    return findings


def discover_standards_docs(root: Path) -> list[dict]:
    candidates = [
        ("docs/agents/project-standards.md", "project_standards"),
        ("CONTEXT.md", "domain_glossary"),
        ("docs/adr", "architecture_decisions"),
    ]
    return [{
        "path": rel,
        "status": "present",
        "kind": kind,
        "consumption_rule": (
            "L1 规划 / 执行 / 评审层 MUST 完整阅读该文件后逐条对照执行；"
            "profile 仅是结构化摘要，与该文件冲突时以该文件为准"
        ),
        "sections": [],
    } for rel, kind in candidates if (root / rel).exists()]


def scan_directory_structure(root: Path) -> dict:
    if not root.is_dir():
        return {"root_files": [], "key_directories": [], "entry_points": []}
    root_files, key_dirs = [], []
    for p in sorted(root.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_file():
            root_files.append(p.name)
        elif p.is_dir() and p.name not in _NOISE_DIRS:
            key_dirs.append(p.name)
    return {
        "root_files": root_files[:50],
        "key_directories": key_dirs[:50],
        "entry_points": [c for c in _ENTRY_CANDIDATES if (root / c).exists()],
    }


def scan_build_commands(root: Path) -> dict:
    """只从显式配置提取命令；无法确认的一律留空，NEVER 编造。"""
    commands = {"build": "", "test": "", "lint": ""}
    scripts = _load_package_json(root).get("scripts")
    if isinstance(scripts, dict):
        manager, _ = detect_package_manager(root)
        runner = {"pnpm": "pnpm", "yarn": "yarn"}.get(manager, "npm")
        for key in ("build", "test", "lint"):
            if key in scripts:
                commands[key] = f"{runner} run {key}"
    makefile = root / "Makefile"
    if makefile.exists():
        targets = re.findall(r"^([A-Za-z0-9_.-]+):", _read(makefile), re.MULTILINE)
        for key in ("build", "test", "lint"):
            if key in targets and not commands[key]:
                commands[key] = f"make {key}"
    if not commands["test"] and "[tool.pytest" in _read(root / "pyproject.toml"):
        commands["test"] = "pytest"
    return commands


def _frontend_summary(front_findings: list[dict], root: Path) -> dict:
    def first_evidence(target: str) -> str:
        for f in front_findings:
            if f["target"] == target and f["evidence_file"]:
                return target
        return NOT_DETECTED

    manager, note = detect_package_manager(root)
    return {
        "path": str(root),
        "framework": next((t for t in ("Vue", "React")
                           if first_evidence(t) != NOT_DETECTED), NOT_DETECTED),
        "ui_library": next((t for t in ("Element Plus", "Ant Design")
                            if first_evidence(t) != NOT_DETECTED), NOT_DETECTED),
        "css_framework": first_evidence("UnoCSS / Tailwind"),
        "state_management": first_evidence("Pinia / Vuex"),
        "package_manager": manager,
        "package_manager_note": note,
    }


def scan(root: Path, frontend: Path | None = None) -> dict:
    root = Path(root)
    frontend = Path(frontend) if frontend else None
    tech_stack = scan_tech_stack(root)
    build_commands = scan_build_commands(root)
    if frontend is not None and frontend != root:
        for item in scan_tech_stack(frontend):
            if not item["evidence_file"]:
                continue  # 前端侧只保留命中项，未命中由后端侧清单统一表达
            tagged = dict(item)
            tagged["target"] = f"frontend:{item['target']}"
            tech_stack.append(tagged)
        front_build = scan_build_commands(frontend)
        for key in ("build", "test", "lint"):
            if not build_commands[key] and front_build[key]:
                build_commands[key] = front_build[key]

    if frontend is not None and frontend != root:
        front_info = _frontend_summary(scan_tech_stack(frontend), frontend)
        mode = "multi_project"
    else:
        front_info = _frontend_summary(scan_tech_stack(root), root)
        front_info["path"] = ""
        mode = "single_project"

    return {
        "mode": mode,
        "repo_path": str(root),
        "tech_stack": tech_stack,
        "standards_doc": discover_standards_docs(root),
        "directory_structure": scan_directory_structure(root),
        "build_commands": build_commands,
        "frontend": front_info,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scan_project.py",
        description="pax-init 确定性项目扫描器（只做证据收集，不做推测）",
    )
    parser.add_argument("root", help="项目根路径")
    parser.add_argument("--frontend", default=None, help="前端项目根路径（前后端分离时）")
    args = parser.parse_args(argv)

    # 保证管道 / 重定向场景下 JSON 始终为 UTF-8（Windows 默认可能是 GBK）
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    root = Path(args.root)
    if not root.is_dir():
        print(json.dumps({
            "error": "path_not_found",
            "root": str(root),
            "message": "路径不存在或不是目录；pax-init 禁止为不存在的路径创建目录",
        }, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(scan(root, args.frontend), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
