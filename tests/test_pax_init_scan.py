"""pax-init 确定性扫描器测试。

覆盖 `skills/pax-init/scripts/scan_project.py` 的诚实性契约：
命中即带证据、未命中标「未检测到」、包管理器优先级、多项目合并、规范文档只登记指针、
幂等且只读。这些断言保证 SKILL.md 里的「扫描诚实铁律」不是空话。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = REPO_ROOT / "skills" / "pax-init" / "scripts" / "scan_project.py"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("pax_init_scan_project", SCAN_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scanner():
    return _load_scanner()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _find(result: dict, target: str) -> dict:
    for item in result["tech_stack"]:
        if item["target"] == target:
            return item
    raise AssertionError(f"target not in scan result: {target}")


def _make_backend(root: Path) -> None:
    _write(root / "pom.xml", """<project>
  <groupId>com.demo</groupId>
  <artifactId>demo</artifactId>
  <properties><java.version>17</java.version></properties>
  <modules><module>ruoyi-generator</module><module>ruoyi-system</module></modules>
  <dependencies>
    <dependency><artifactId>spring-boot-starter-web</artifactId></dependency>
  </dependencies>
</project>
""")
    (root / "ruoyi-generator").mkdir(parents=True, exist_ok=True)


def _make_frontend(root: Path) -> None:
    _write(root / "package.json", json.dumps({
        "name": "demo-web",
        "scripts": {"build": "vite build", "test": "vitest", "lint": "eslint ."},
        "dependencies": {"vue": "3.4.0", "element-plus": "2.5.0"},
        "devDependencies": {"vite": "5.0.0", "typescript": "5.3.0"},
    }))
    _write(root / "tsconfig.json", "{}")
    _write(root / "vite.config.ts", "export default {}")
    _write(root / "pnpm-lock.yaml", "")
    _write(root / "src" / "main.ts", "")


def test_hit_findings_carry_evidence_file(scanner, tmp_path):
    backend = tmp_path / "backend"
    _make_backend(backend)

    result = scanner.scan(backend)

    maven = _find(result, "Java / Maven")
    assert maven["evidence_file"].endswith("pom.xml")
    assert maven["extracted"]["java_version"] == "17"
    assert maven["extracted"]["modules"] == ["ruoyi-generator", "ruoyi-system"]

    spring = _find(result, "Spring Boot")
    assert spring["extracted"]["starters"] == ["spring-boot-starter-web"]

    ruoyi = _find(result, "RuoYi 框架")
    assert ruoyi["extracted"]["code_generator"] == "ruoyi-generator"


def test_absent_findings_are_explicitly_not_detected(scanner, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    result = scanner.scan(empty)

    for item in result["tech_stack"]:
        assert item["evidence_file"] is None, item
        assert item["extracted"] == scanner.NOT_DETECTED, item
    assert result["standards_doc"] == []


def test_package_manager_priority_and_lock_trap(scanner, tmp_path):
    project = tmp_path / "web"
    project.mkdir()
    _write(project / "package.json", '{"name": "w"}')

    # 仅 package.json → 未检测到（按规则不猜）
    assert scanner.detect_package_manager(project) == (
        scanner.NOT_DETECTED, "仅有 package.json 无 lock 文件，按规则标未检测到")

    # npm lock 存在
    _write(project / "package-lock.json", "{}")
    assert scanner.detect_package_manager(project)[0] == "npm"

    # pnpm lock 优先于 npm lock
    _write(project / "pnpm-lock.yaml", "")
    assert scanner.detect_package_manager(project) == ("pnpm", "")


def test_multi_project_merges_frontend_and_build_commands(scanner, tmp_path):
    backend = tmp_path / "backend"
    frontend = tmp_path / "frontend"
    _make_backend(backend)
    _make_frontend(frontend)

    result = scanner.scan(backend, frontend)

    assert result["mode"] == "multi_project"
    targets = [i["target"] for i in result["tech_stack"]]
    assert "frontend:Vue" in targets
    assert "frontend:Vite" in targets
    # 前端未命中项被过滤，避免噪声
    assert "frontend:Go" not in targets
    assert result["frontend"]["framework"] == "Vue"
    assert result["frontend"]["package_manager"] == "pnpm"
    assert result["build_commands"]["build"] == "pnpm run build"
    assert result["build_commands"]["test"] == "pnpm run test"


def test_standards_doc_is_pointer_not_content(scanner, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    _write(root / "docs" / "agents" / "project-standards.md", "# 内部规范正文")
    (root / "docs" / "adr").mkdir(parents=True, exist_ok=True)

    result = scanner.scan(root)

    kinds = {d["kind"] for d in result["standards_doc"]}
    assert kinds == {"project_standards", "architecture_decisions"}
    for doc in result["standards_doc"]:
        assert doc["status"] == "present"
        assert "以该文件为准" in doc["consumption_rule"]
        # 只登记指针，绝不携带原文
        assert "内部规范正文" not in json.dumps(doc, ensure_ascii=False)


def test_scan_is_deterministic_and_read_only(scanner, tmp_path):
    root = tmp_path / "proj"
    _make_backend(root)

    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
    first = json.dumps(scanner.scan(root), ensure_ascii=False, sort_keys=True)
    second = json.dumps(scanner.scan(root), ensure_ascii=False, sort_keys=True)
    after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))

    assert first == second
    assert before == after  # 扫描不得写入目标项目


def test_main_rejects_missing_path(scanner, tmp_path, capsys):
    missing = tmp_path / "does-not-exist"

    code = scanner.main([str(missing)])

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "path_not_found"
